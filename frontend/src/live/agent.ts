// In-browser agent (#/live): the device's pipeline on the user's own camera, in the page.
//   1 getUserMedia -> 2 canvas (resize, raw brightness / IR numbers) -> 3 MediaPipe Tasks JS
//   -> 4 YOLO in a worker -> 6-12 the device's Python (edge_agent/web/bridge.py) in Pyodide
//   -> 13 HUD (HudScreen via HudSource) + 14 batches posted with the user's token.
// Frames stay in this page's memory (video element + one canvas); only the numbers above reach
// Python and only metadata JSON leaves the browser.
// The loop watches itself (M71, watchdog.ts): when the browser stops calling it, frames are pulled
// with a timer; a camera that gives none is reported lost and asked for again; a frame that fails
// on this side is reported to Python like one that fails there.
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { ApiError, API_URL, getWebThresholds, postWebBatch, webDeviceId, refreshSession, postWebBatchOnLeave } from "../lib/api";
import type { HudEnrollment, HudSnapshot, Session, TripSummary, VehicleAction } from "../lib/types";
import { newDriveCode } from "../drive/sim";
import { DRIVE_SIM_URL, type FeedbackResult, type HudSource, type TripEnd } from "../hud/edge";
import {
  bbox,
  channelDiff,
  concatFaces,
  letterboxGeometry,
  lumaSpread,
  meanLuma,
  sharpness,
  toChw,
  toPixels,
} from "./measure";
import { frameTimeMs, type FrameMetadata } from "./frameTime";
import { chooseDelegate, gpuKind, webglRenderer, type GpuKind, type YoloProvider } from "./gpu";
import { YoloPacer } from "./pace";
import { YoloWatch } from "./yoloWatch";
import { urgentKey } from "../hud/hudModel";
import { PerfWindow, type PerfSnapshot, type PerfTotals } from "./perf";
import { RepeatCheck } from "./frozen";
import { tripId } from "./tripId";
import { LoopWatchdog, type CameraTrack } from "./watchdog";
import type { YoloRequest, YoloResponse } from "./yolo.worker";
import { DEFAULTS } from "../lib/defaults";

// Pinned versions: the Python side is tested against this Pyodide (numpy, pyyaml). No OpenCV since M45
// (11.7 MB less to download): head pose and box suppression run in numpy (edge_agent/perception/geometry.py).
// Both runtimes are served by the app itself (M99: `npm run prepare-live` puts them under public/runtime,
// scripts/web-runtime.mjs), not by a CDN: no third party's code runs in the page that holds the camera
// stream and the login token, and the page starts without reaching anything but its own server.
/** Absolute, for the dynamic import of pyodide.mjs; read when the page starts a trip, not at import. */
const runtimeUrl = (part: string) => new URL(`${import.meta.env.BASE_URL}runtime/${part}`, location.href).href;
const PYODIDE_PACKAGES = ["numpy", "pyyaml"]; // not sqlite3: the page has no outbox (publisher.py imports it there only)
const BASE = import.meta.env.BASE_URL;
// Asked for before Python has loaded (the camera opens meanwhile), so from the build's copy of
// thresholds.yaml: capture.web_camera_width / web_camera_height / camera_fps.
const CAMERA: MediaStreamConstraints = {
  video: {
    width: { ideal: DEFAULTS.camera.width },
    height: { ideal: DEFAULTS.camera.height },
    frameRate: { ideal: DEFAULTS.camera.fps },
    facingMode: "user",
  },
  audio: false,
};
const WATCH_LOOKS = 3; // looks at the loop per capture.frame_timeout_s

// End-to-end test builds only (VITE_E2E=1; production builds drop this code): block 3 reads
// synthetic landmark numbers that the Playwright test puts on window.__dgFeed instead of running
// MediaPipe, YOLO is off, and the latest HUD state is mirrored on window.__dgState. The camera is
// Chrome's fake device and blocks 6-14 run unchanged, so no face image is needed anywhere.
const E2E = import.meta.env.VITE_E2E === "1";

/** One frame of synthetic faces: 478 x (x, y, z) pixels per face, eyeBlink (left, right) and browOuterUp per face. */
export interface E2EFeed {
  faces: number[][];
  blink: number[];
  brow: number[];
}
declare global {
  interface Window {
    __dgFeed?: E2EFeed | null;
    __dgState?: unknown;
  }
}

// What the driver sees while starting: two steps, no component names. The three downloads
// (Python, face model, phone model) run side by side from the moment the page asks for the camera
// (M50) and are one "getting ready" step, whose progress is the share of them that finished.
export const STEPS: Record<"camera" | "prepare", string> = {
  camera: "Mở camera",
  prepare: "Đang chuẩn bị (lần đầu tải khoảng 30 MB, các lần sau nhanh hơn)",
};
export interface Step {
  step: keyof typeof STEPS | "ready";
  progress: number; // 0..1 of the "getting ready" step
}

/** What to show while starting: "camera" until the camera is on (the downloads already run behind
 *  it), then "prepare" with the share of the downloads that finished. */
export function loadingStep(cameraOn: boolean, done: number, parts: number): Step {
  return cameraOn ? { step: "prepare", progress: done / parts } : { step: "camera", progress: 0 };
}

export interface LiveStats {
  level: number;
  fps: number;
  yoloMs: number | null;
  phoneOn: boolean;
  sent: number;
  pending: number;
  dropped: number; // POST bodies pushed out of a full queue (publisher.max_queue), oldest first
  refused: number; // records the backend will never take (HTTP 400 / 413 / 422), dropped one by one (M97)
  sendError: string | null;
  measures: Measures | null;
  enrollment: HudEnrollment | null;
  lastError: string | null; // M28: last frame error "Type · file:line" (code location only)
  perf: PerfSnapshot | null; // M49: time per stage of the loop over the last seconds
  totals: PerfTotals | null; // M67: counted since the loop started (long runs)
  startup: StartupMs | null; // M67: how long starting took
  recovery: Recovery; // M71
}

/** What the loop had to do to keep getting frames since it started (M71; counts only). */
export interface Recovery {
  pulls: number; // times the browser's frame callback went quiet and a timer took over
  reopens: number; // times the camera was asked for again
  yoloRestarts: number; // times the phone detector's worker stopped answering and was replaced
}

/** Start-up, in ms from the call to `LiveAgent.start` to each part being ready (M67; local only). */
export interface StartupMs {
  camera: number | null; // the camera stream plays
  python: number | null; // Pyodide, its packages and the agent
  face_model: number | null; // MediaPipe created
  phone_model: number | null; // YOLO session ready; null = no detector
  first_frame: number | null; // the first frame went through the whole loop
}

export interface Measures {
  face: boolean;
  ear: number | null;
  mar: number | null;
  yaw: number | null;
  pitch: number | null;
  phone: boolean | null;
}

interface Settings {
  capture: { frame_timeout_s: number; reconnect_interval_s: number; camera_fps: number; frozen_stride: number; max_frame_age_s: number };
  target_width: number;
  sample_stride: number; // preprocess.sample_stride: the whole-image numbers, as the device takes them
  eye_blink_missing: number; // eye_state.web_blink_missing
  vehicle: { poll_s: number; stale_s: number }; // context.vehicle_poll_s / vehicle_signal_stale_s
  landmarks: {
    num_faces: number;
    min_face_detection_confidence: number;
    min_face_presence_confidence: number;
    min_tracking_confidence: number;
    blendshapes: boolean;
  };
  phone: { input_size: number; target_fps: number; num_threads: number; web_gpu: boolean; gpu_target_fps: number; run_timeout_s: number; load_timeout_s: number; restart_limit: number };
  flush_interval_s: number;
  send_timeout_s: number; // publisher.timeout_s: a POST gives up after this (M97)
  max_queue: number; // publisher.max_queue: POST bodies kept while the backend cannot be reached
  config_poll_s: number; // ask the backend for tuned thresholds this often (M47); 0 = only at start
  problems: string[];
}

// The few Pyodide calls used here (loaded from the CDN at run time, not bundled).
interface PyAgent {
  settings(): string;
  frame(...args: unknown[]): string;
  frame_error(t: number, error: string): string;
  phone_output(...args: unknown[]): number;
  false_alarm(eventId: string): string;
  camera(lost: boolean): void;
  camera_attempts(attempts: number): void;
  hud_state(): string;
  end_trip(): string;
  vehicle(action: string): string;
  vehicle_signal(speed: number, turn: string | null): void;
  take_batch(): string | undefined;
  idle(t: number): void;
  take_heartbeat(): string | undefined;
  perf(doc: string): boolean;
  expect_phone(expected: boolean): void;
  offer_thresholds(version: number, values: string): boolean;
  destroy(): void;
}
interface Pyodide {
  unpackArchive(buf: ArrayBuffer, format: string, opts: { extractDir: string }): void;
  runPython(code: string): unknown;
  pyimport(name: string): { WebAgent: { callKwargs(...args: unknown[]): PyAgent } };
  toPy(obj: unknown): unknown;
}

// One default mode (bridge scenario "sim"): speed and turn signal come from the web driving controls
// (#/drive?code=<driveCode>, relayed by the backend, M31) or else from the driving simulator
// (tools/drive_sim.py on 127.0.0.1); both polled by pollSim. None = parked at 0 km/h. Time of day =
// real clock. How often, and how old a remote reading may be before it is not passed on (the vehicle
// signal goes stale, M26): settings.vehicle, i.e. context.vehicle_poll_s / vehicle_signal_stale_s.
async function loadPython(session: Session | null): Promise<{ agent: PyAgent; settings: Settings }> {
  const PYODIDE_URL = runtimeUrl("pyodide/");
  const mod = (await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`)) as {
    loadPyodide(o: { indexURL: string; packages?: string[] }): Promise<Pyodide>;
  };
  // M67: the packages download while the runtime starts (they used to wait for it), and so do the
  // agent's own code and the tuned thresholds.
  const [py, zip, tuned] = await Promise.all([
    mod.loadPyodide({ indexURL: PYODIDE_URL, packages: PYODIDE_PACKAGES }),
    fetch(`${BASE}py/edge_agent.zip`).then((r) => {
      if (!r.ok) throw new Error(`edge_agent.zip: HTTP ${r.status}`);
      return r.arrayBuffer();
    }),
    session ? getWebThresholds(session).catch(() => null) : Promise.resolve(null),
  ]);
  py.unpackArchive(zip, "zip", { extractDir: "/home/pyodide/dg" });
  py.runPython('import sys; sys.path.insert(0, "/home/pyodide/dg")');
  const deviceId = session ? webDeviceId(session.username) : "web-guest";
  const overrides = py.toPy(tuned?.values ?? {});
  const agent = py
    .pyimport("edge_agent.web.bridge")
    .WebAgent.callKwargs(deviceId, tripId(), { overrides, thresholds_version: tuned?.version ?? 0 });
  const settings = JSON.parse(agent.settings()) as Settings;
  if (settings.problems.length) console.warn("[live] tuned thresholds ignored:", settings.problems);
  return { agent, settings };
}

const DELEGATE_KEY = "dg.landmarks.delegate"; // "GPU" | "CPU" in localStorage: force one (measurements)
const PROVIDER_KEY = "dg.phone.provider"; // "webgpu" | "wasm" in localStorage: force one (measurements)

function forced(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null; // storage blocked: no override
  }
}

/** Block 3's files, fetched ahead of the settings Python hands over: the model itself, and MediaPipe's
 *  wasm runtime into the browser's HTTP cache (createFromOptions loads it from there). */
async function loadFaceFiles(): Promise<{ fileset: Awaited<ReturnType<typeof FilesetResolver.forVisionTasks>>; model: Uint8Array }> {
  const [fileset, model] = await Promise.all([
    FilesetResolver.forVisionTasks(runtimeUrl("mediapipe")),
    fetch(`${BASE}models/face_landmarker.task`).then(async (r) => {
      if (!r.ok) throw new Error(`face_landmarker.task: HTTP ${r.status}`);
      return new Uint8Array(await r.arrayBuffer());
    }),
  ]);
  // Best effort: a failure here only means the runtime is downloaded a moment later.
  await Promise.all([fileset.wasmLoaderPath, fileset.wasmBinaryPath].map((url) => fetch(url).then((r) => r.arrayBuffer()).catch(() => undefined)));
  return { fileset, model };
}

interface YoloSession {
  worker: Worker;
  threads: number;
  provider: YoloProvider;
}

// The backend will never accept this content (edge_agent/io/publisher.py DROP_STATUSES). Anything else
// that is not a success (401, 403, 429, 5xx, no answer) is kept and tried again.
const DROP_STATUSES: readonly number[] = [400, 413, 422];
// A closing page may have about 64 KiB of `keepalive` request bodies in flight (Fetch standard); a little
// is left for the headers.
const KEEPALIVE_BUDGET_BYTES = 60000;

/** A POST body of several records as one body per record, in order; a body of one record (or one that
 *  is not a batch) as itself. */
export function splitBatch(body: string): string[] {
  try {
    const { device_id, ...kinds } = JSON.parse(body) as Record<string, unknown>;
    const singles: string[] = [];
    for (const [kind, records] of Object.entries(kinds)) {
      if (!Array.isArray(records)) return [body]; // a heartbeat, or something this page did not build
      for (const record of records) singles.push(JSON.stringify({ device_id, [kind]: [record] }));
    }
    return singles.length > 1 ? singles : [body];
  } catch {
    return [body];
  }
}

export class LiveAgent implements HudSource {
  address = "trình duyệt này";
  /** Pairing code for the web driving controls (#/drive?code=...), shown on the camera card. */
  readonly driveCode = newDriveCode();
  private snap: HudSnapshot = { connected: false, level: 0, reasons: [], alerts: [] };
  private stats: LiveStats = { level: 0, fps: 0, yoloMs: null, phoneOn: false, sent: 0, pending: 0, dropped: 0, refused: 0, sendError: null, measures: null, enrollment: null, lastError: null, perf: null, totals: null, startup: null, recovery: { pulls: 0, reopens: 0, yoloRestarts: 0 } };
  private stopped = false;
  private frameId = 0;
  private lastTsMs = -1;
  private lastVideoTime = -1;
  private yolo: Worker | null = null; // set once the detector's session is ready (attachYolo)
  private yoloThreads: number | null = null;
  private yoloProvider: YoloProvider | null = null;
  private yoloBusy = false;
  private yoloPacer: YoloPacer;
  private yoloWatch: YoloWatch; // a worker that stops answering is replaced
  private pendingBodies: string[] = [];
  private heartbeatBody: string | null = null; // M33: newest heartbeat not sent yet (never queued)
  private sending = false;
  private flushTimer: number | undefined;
  private refreshAt = 0; // ms epoch: the login token is exchanged for a new one from then on (M97)
  private configTimer: number | undefined;
  private simTimer: number | undefined;
  private simBusy = false;
  private canvas = document.createElement("canvas");
  private ctx: CanvasRenderingContext2D;
  private yoloCanvas = document.createElement("canvas");
  private yoloCtx: CanvasRenderingContext2D;
  private perf = new PerfWindow(); // M49
  private lastPresented: number | null = null; // requestVideoFrameCallback's frame counter
  private yoloResultT: number | null = null; // frame time of the YOLO result in use
  private lastFrameMs = -Infinity; // time of the last frame (frameTimeMs), M50
  private listeners = new Set<(snap: HudSnapshot) => void>(); // M50: the HUD hears of an alert at once
  private pushed = "";
  private watch: LoopWatchdog; // M71
  private repeat: RepeatCheck; // M83: the camera hands the same image again and again
  private watchTimer: number | undefined;
  private pullTimer: number | undefined; // set while a timer drives the loop
  private frameCallback: number | null = null; // the pending requestVideoFrameCallback / requestAnimationFrame
  private cameraLost = false;
  private reopening = false;
  private recovery: Recovery = { pulls: 0, reopens: 0, yoloRestarts: 0 };

  private constructor(
    private video: HTMLVideoElement,
    private stream: MediaStream,
    private py: PyAgent,
    private settings: Settings,
    private landmarker: FaceLandmarker | null, // null in end-to-end test builds (E2E)
    private session: Session | null,
    private delegate: PerfSnapshot["landmarks_delegate"] = null, // what MediaPipe was created with
    private gpu: GpuKind | null = null, // what draws WebGL here (M51)
    private startup: { t0: number; ms: StartupMs } | null = null, // M67
  ) {
    this.ctx = this.canvas.getContext("2d", { willReadFrequently: true })!;
    this.yoloCtx = this.yoloCanvas.getContext("2d", { willReadFrequently: true })!;
    this.yoloPacer = new YoloPacer(settings.phone.target_fps);
    this.yoloWatch = new YoloWatch(settings.phone.run_timeout_s * 1000, settings.phone.restart_limit);
    const cap = settings.capture;
    this.watch = new LoopWatchdog(cap.frame_timeout_s * 1000, cap.reconnect_interval_s * 1000, performance.now());
    this.repeat = new RepeatCheck(cap.frozen_stride);
  }

  /** Ask for the camera, load the models, start the loop. onStep reports progress for the setup screen. */
  static async start(
    video: HTMLVideoElement,
    session: Session | null,
    onStep: (s: Step) => void,
  ): Promise<LiveAgent> {
    // M50: Python, the face model and the phone model do not depend on each other or on the camera,
    // so all three load while the browser asks for the camera instead of one after the other.
    const t0 = performance.now();
    const startup: StartupMs = { camera: null, python: null, face_model: null, phone_model: null, first_frame: null };
    const mark = (part: keyof StartupMs) => void (startup[part] = Math.round(performance.now() - t0));
    const parts = E2E ? 1 : 3;
    let done = 0;
    let cameraOn = false;
    const report = () => onStep(loadingStep(cameraOn, done, parts));
    const part = <T>(p: Promise<T>): Promise<T> => {
      const counted = p.then((v) => {
        done += 1;
        report();
        return v;
      });
      counted.catch(() => undefined); // awaited below; a camera refusal must not leave it unhandled
      return counted;
    };
    report();
    const python = part(loadPython(session));
    const faceFiles = E2E ? null : part(loadFaceFiles());
    const yolo = E2E ? null : part(LiveAgent.loadYolo());
    const dropYolo = () => void yolo?.then((worker) => worker?.terminate()).catch(() => undefined);

    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia(CAMERA);
    } catch (err) {
      dropYolo();
      throw err;
    }
    try {
      video.srcObject = stream;
      video.muted = true;
      video.playsInline = true;
      await video.play();
      cameraOn = true;
      mark("camera");
      report();
      const { agent, settings } = await python;
      mark("python");
      agent.expect_phone(!E2E); // also when YOLO fails to load: then Python reports it (M50)
      if (E2E) {
        const live = new LiveAgent(video, stream, agent, settings, null, session, null, null, { t0, ms: startup });
        live.run();
        onStep({ step: "ready", progress: 1 });
        return live;
      }
      const lm = settings.landmarks;
      const { fileset, model } = await faceFiles!;
      const options = {
        runningMode: "VIDEO" as const,
        numFaces: lm.num_faces,
        minFaceDetectionConfidence: lm.min_face_detection_confidence,
        minFacePresenceConfidence: lm.min_face_presence_confidence,
        minTrackingConfidence: lm.min_tracking_confidence,
        outputFaceBlendshapes: lm.blendshapes,
      };
      let landmarker: FaceLandmarker;
      // M51: the GPU delegate only where a real GPU draws WebGL; on a software rasterizer it is several
      // times slower than the CPU delegate. Both are recorded with the loop timings (M49).
      const gpu = gpuKind(webglRenderer());
      let delegate = chooseDelegate(gpu, forced(DELEGATE_KEY));
      try {
        landmarker = await FaceLandmarker.createFromOptions(fileset, { baseOptions: { modelAssetBuffer: model, delegate }, ...options });
      } catch (err) {
        if (delegate === "CPU") throw err;
        delegate = "CPU";
        landmarker = await FaceLandmarker.createFromOptions(fileset, { baseOptions: { modelAssetBuffer: model, delegate: "CPU" }, ...options });
      }
      mark("face_model");
      const live = new LiveAgent(video, stream, agent, settings, landmarker, session, delegate, gpu, { t0, ms: startup });
      live.run();
      // M67: the loop does not wait for the phone detector. Its session is built (and on WebGPU warmed
      // up, most of a second) while the face is already monitored; frames until then have no phone
      // answer, as the first frames always had, and Python reports a detector that never comes (M50).
      void yolo!
        .then((worker) => LiveAgent.createYolo(worker, settings.phone))
        .then((y) => {
          if (!y) return;
          mark("phone_model");
          live.attachYolo(y);
        })
        .catch(() => undefined);
      onStep({ step: "ready", progress: 1 });
      return live;
    } catch (err) {
      stream.getTracks().forEach((t) => t.stop());
      dropYolo();
      throw err;
    }
  }

  /** YOLO in a worker; without it the agent still runs, phone detection off (Python reports that, M50).
   *  Resolves once the model is downloaded; `createYolo` then builds the session. */
  private static async loadYolo(timeoutMs = 0): Promise<Worker | null> {
    const worker = new Worker(new URL("./yolo.worker.ts", import.meta.url), { type: "module" });
    const init: YoloRequest = { type: "init", modelUrl: `${BASE}models/yolov8n.onnx` };
    if ((await LiveAgent.askYolo(worker, init, timeoutMs))?.type === "fetched") return worker;
    worker.terminate();
    return null;
  }

  /** The session: on WebGPU where phone.web_gpu allows it and a real GPU adapter exists, else on wasm
   *  with phone.num_threads threads where the page may use threads. */
  private static async createYolo(worker: Worker | null, cfg: Settings["phone"]): Promise<YoloSession | null> {
    if (!worker) return null;
    const request: YoloRequest = { type: "create", threads: cfg.num_threads, webgpu: cfg.web_gpu, forced: forced(PROVIDER_KEY), size: cfg.input_size };
    const answer = await LiveAgent.askYolo(worker, request, cfg.load_timeout_s * 1000);
    if (answer?.type === "ready") return { worker, threads: answer.threads, provider: answer.provider };
    worker.terminate();
    return null;
  }

  /** Where the detector runs decides how often: phone.web_gpu_target_fps on WebGPU, phone.target_fps on
   *  wasm, where a run costs several times the CPU (config/thresholds.yaml has the numbers). */
  private setYoloProvider(provider: YoloProvider) {
    const cfg = this.settings.phone;
    this.yoloProvider = provider;
    this.yoloPacer = new YoloPacer(provider === "webgpu" ? cfg.gpu_target_fps : cfg.target_fps);
  }

  /** The phone detector is ready: frames go to it from now on. */
  private attachYolo(y: YoloSession) {
    if (this.stopped) {
      y.worker.terminate();
      return;
    }
    [this.yolo, this.yoloThreads] = [y.worker, y.threads];
    this.setYoloProvider(y.provider);
    this.stats.phoneOn = true;
    y.worker.onmessage = (e: MessageEvent<YoloResponse>) => this.onYolo(e.data);
    y.worker.onerror = () => void (this.yoloBusy = false);
  }

  /** One request to the worker and its answer; null when it failed, or gave none within timeoutMs
   *  (0 = waits as long as it takes: the first download, before the settings are known). */
  private static askYolo(worker: Worker, request: YoloRequest, timeoutMs = 0): Promise<YoloResponse | null> {
    return new Promise((resolve) => {
      const timer = timeoutMs > 0 ? window.setTimeout(() => done(null, `no answer to "${request.type}" in ${timeoutMs} ms`), timeoutMs) : undefined;
      const done = (answer: YoloResponse | null, why?: string) => {
        window.clearTimeout(timer);
        if (why) console.warn("[live] phone detector disabled:", why);
        resolve(answer);
      };
      worker.onmessage = (e: MessageEvent<YoloResponse>) => (e.data.type === "error" ? done(null, e.data.message) : done(e.data));
      worker.onerror = () => done(null);
      worker.postMessage(request);
    });
  }

  /** The worker did not answer its run in phone.web_run_timeout_s (yoloWatch.ts): it is terminated,
   *  which is the only way to stop a run, and a new one is built beside the running loop. Frames have
   *  no phone answer meanwhile; a detector that does not come back is reported by Python (M50). */
  private checkYolo() {
    const verdict = this.yoloWatch.check(performance.now());
    if (verdict === "ok" || this.stopped) return;
    console.warn(`[live] phone detector gave no answer in ${this.settings.phone.run_timeout_s} s:`, verdict === "restart" ? "starting it again" : "given up");
    this.yolo?.terminate();
    this.yolo = null;
    this.yoloBusy = false;
    this.stats.phoneOn = false;
    this.stats.yoloMs = null;
    if (verdict !== "restart") return;
    this.recovery.yoloRestarts += 1;
    const cfg = this.settings.phone;
    void LiveAgent.loadYolo(cfg.load_timeout_s * 1000)
      .then((worker) => LiveAgent.createYolo(worker, cfg))
      .then((y) => y && this.attachYolo(y))
      .catch(() => undefined);
  }

  // ------------------------------------------------------------------ HudSource
  async state(): Promise<HudSnapshot> {
    return this.snap;
  }

  /** Called in the frame that brings a new alert or another change the driver must hear at once
   *  (hudModel.urgentKey), instead of at the HUD's next poll (M50). Returns the unsubscribe. */
  subscribe(listener: (snap: HudSnapshot) => void): () => void {
    this.listeners.add(listener);
    return () => void this.listeners.delete(listener);
  }

  async falseAlarm(eventId: string): Promise<FeedbackResult> {
    const r = this.py.false_alarm(eventId);
    if (r === "ok") void this.flush();
    return r === "ok" ? "recorded" : (r as FeedbackResult);
  }

  /** "Đổi tài xế" (bridge.vehicle). */
  async vehicle(action: VehicleAction): Promise<boolean> {
    const ok = this.py.vehicle(action) === "ok";
    if (ok && action === "change_driver") void this.flush(); // driver_changed event
    return ok;
  }

  /** "Kết thúc chuyến": the trip summary (block 11), sent with the user's token, then the camera stops.
   *  Guest mode keeps it in this browser only. */
  async endTrip(): Promise<TripEnd> {
    const summary = JSON.parse(this.py.end_trip()) as TripSummary;
    let delivery: TripEnd["delivery"] = "local";
    if (this.session) {
      await this.flush();
      delivery = this.pendingBodies.length === 0 && !this.stats.sendError ? "sent" : "failed";
    }
    await this.stop();
    return { summary, delivery };
  }

  /** The page is going away with the trip running (tab closed, reload; M100). Nothing asynchronous will
   *  finish, so the trip is ended in this turn: Python builds the summary, the camera is let go, and
   *  what is waiting goes out with `keepalive` requests the browser finishes by itself: the "ended"
   *  heartbeat first (so the fleet shows an ended trip, not a lost vehicle), then the batches, oldest
   *  first, while they fit in what a browser lets a closing page send. Guest mode sends nothing.
   *  Returns how many bodies were sent and how many did not fit. */
  leave(): { sent: number; left: number } {
    if (this.stopped) return { sent: 0, left: 0 };
    this.stopped = true;
    window.clearInterval(this.flushTimer);
    window.clearInterval(this.configTimer);
    window.clearInterval(this.simTimer);
    window.clearInterval(this.watchTimer);
    this.stopPulling();
    this.py.end_trip();
    this.py.idle(performance.now() / 1000);
    const beat = this.py.take_heartbeat() ?? this.heartbeatBody;
    for (let body = this.py.take_batch(); body; body = this.py.take_batch()) this.pendingBodies.push(body);
    this.stream.getTracks().forEach((t) => t.stop());
    this.video.srcObject = null;
    let sent = 0;
    let left = 0;
    if (this.session) {
      let room = KEEPALIVE_BUDGET_BYTES;
      for (const body of [...(beat ? [beat] : []), ...this.pendingBodies]) {
        const size = new Blob([body]).size;
        if (size > room) {
          left += 1;
          continue;
        }
        room -= size;
        postWebBatchOnLeave(this.session, body);
        sent += 1;
      }
    }
    this.pendingBodies = [];
    this.heartbeatBody = null;
    return { sent, left };
  }

  getStats(): LiveStats {
    return { ...this.stats, pending: this.pendingBodies.length, perf: this.perfSnapshot(), totals: this.perf.totals(), startup: this.startup?.ms ?? null, recovery: { ...this.recovery } };
  }

  private perfSnapshot(): PerfSnapshot {
    return { ...this.perf.snapshot(this.delegate, this.yolo ? this.yoloThreads : null), gpu: this.gpu, yolo_provider: this.yoloProvider };
  }

  // ------------------------------------------------------------------ loop
  private run() {
    this.listenToCamera();
    this.flushTimer = window.setInterval(() => void this.flush(), this.settings.flush_interval_s * 1000);
    if (this.session && this.settings.config_poll_s > 0)
      this.configTimer = window.setInterval(() => void this.pollThresholds(), this.settings.config_poll_s * 1000);
    this.simTimer = window.setInterval(() => void this.pollSim(), this.settings.vehicle.poll_s * 1000);
    this.watchTimer = window.setInterval(() => {
      this.checkLoop();
      this.checkYolo();
    }, (this.settings.capture.frame_timeout_s * 1000) / WATCH_LOOKS);
    this.armFrameCallback();
  }

  /** A camera that ends (unplugged, permission revoked) is acted on at once, not at the next look. */
  private listenToCamera() {
    this.stream.getVideoTracks()[0]?.addEventListener("ended", () => this.checkLoop());
  }

  /** Ask the browser for the next camera frame; a request still pending is dropped first. */
  private armFrameCallback() {
    if (this.stopped) return;
    const video = this.video;
    // requestVideoFrameCallback passes (now, metadata); requestAnimationFrame only (now).
    if ("requestVideoFrameCallback" in video) {
      if (this.frameCallback != null) video.cancelVideoFrameCallback(this.frameCallback);
      this.frameCallback = video.requestVideoFrameCallback((_now, metadata) => this.onFrame(metadata, false));
    } else {
      if (this.frameCallback != null) cancelAnimationFrame(this.frameCallback);
      this.frameCallback = requestAnimationFrame(() => this.onFrame(undefined, false));
    }
  }

  /** One look at the video: a frame not seen yet goes through the loop. pulled: called by the
   *  watchdog's timer, not by the browser's frame callback. */
  private onFrame(metadata: FrameMetadata | undefined, pulled: boolean) {
    if (this.stopped) return;
    if (!pulled) this.frameCallback = null;
    if (this.video.readyState >= 2 && this.video.currentTime !== this.lastVideoTime) {
      this.lastVideoTime = this.video.currentTime;
      this.watch.frame(performance.now(), pulled);
      if (!pulled) this.stopPulling(); // the browser calls again
      this.setCameraLost(this.watch.still);
      const presented = metadata?.presentedFrames;
      if (presented != null) {
        // Frames the camera delivered since the last one processed: more than 1 = the loop skipped some.
        if (this.lastPresented != null) this.perf.cameraFrames(presented - this.lastPresented);
        this.lastPresented = presented;
      }
      try {
        this.processFrame(metadata);
      } catch (err) {
        console.error("[live] frame failed", err);
        this.frameError(err);
      }
    }
    if (!pulled) this.armFrameCallback();
  }

  /** A frame failed on this side (MediaPipe, the canvas, the call into Python). Python hears of it like
   *  of a frame failing there (M28): failing for a while = "processing error" on the HUD and to the
   *  backend. Only the error's class name is passed on. */
  private frameError(err: unknown) {
    try {
      this.showFrame(JSON.parse(this.py.frame_error(performance.now() / 1000, err instanceof Error ? err.name : "Error")));
    } catch {
      // Python does not answer either: the HUD says the loop stopped after its own timeout
    }
  }

  // ------------------------------------------------------------------ loop watch (M71)
  /** Is the loop still getting frames? Called on a timer, and when the camera track ends. */
  private checkLoop() {
    if (this.stopped) return;
    const track = this.stream.getVideoTracks()[0];
    const camera: CameraTrack = !track || track.readyState === "ended" ? "ended" : track.muted ? "muted" : "live";
    const verdict = this.watch.check(performance.now(), camera, document.visibilityState !== "hidden");
    if (!verdict.pull) this.stopPulling();
    else if (this.pullTimer === undefined) {
      this.recovery.pulls += 1;
      this.armFrameCallback(); // in case the browser dropped the pending request
      this.pullTimer = window.setInterval(() => this.onFrame(undefined, true), 1000 / this.settings.capture.camera_fps);
    }
    this.setCameraLost(verdict.lost);
    if (verdict.reopen) void this.reopenCamera(verdict.reopen);
  }

  private stopPulling() {
    window.clearInterval(this.pullTimer);
    this.pullTimer = undefined;
  }

  /** The camera gives no frames / gives them again: Python tells the HUD and the backend. */
  private setCameraLost(lost: boolean) {
    if (lost === this.cameraLost) return;
    this.cameraLost = lost;
    this.py.camera(lost);
    this.showHud();
  }

  /** The HUD state as Python has it now: no frame brings it while the camera is lost. */
  private showHud() {
    this.show(JSON.parse(this.py.hud_state()) as HudSnapshot);
  }

  /** Ask for the lost camera again, as block 1 does on the device every capture.reconnect_interval_s. */
  private async reopenCamera(attempt: number) {
    if (this.reopening) return;
    this.reopening = true;
    this.recovery.reopens += 1;
    this.py.camera_attempts(attempt);
    this.showHud();
    try {
      const stream = await navigator.mediaDevices.getUserMedia(CAMERA);
      if (this.stopped) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      this.stream.getTracks().forEach((t) => t.stop());
      this.stream = stream;
      this.video.srcObject = stream;
      this.lastPresented = null; // the frame counter starts again with the new stream
      this.watch.reopened(performance.now());
      this.listenToCamera();
      this.armFrameCallback();
      // Not awaited: a play() that never settles must not block the next attempt.
      void this.video.play().catch(() => undefined);
    } catch {
      // still lost (unplugged, refused, in use): asked again after capture.reconnect_interval_s
    } finally {
      this.reopening = false;
    }
  }

  private processFrame(metadata?: FrameMetadata) {
    const vw = this.video.videoWidth;
    const vh = this.video.videoHeight;
    if (!vw || !vh) return;
    const started = performance.now(); // M49: the stages below are timed, numbers only
    // M50: the frame's own time (when the camera took it), not the time the loop got round to it.
    const frameMs = frameTimeMs(started, metadata, this.lastFrameMs, this.settings.capture.max_frame_age_s * 1000);
    this.lastFrameMs = frameMs;
    if (frameMs < started) this.perf.add("camera_lag", started - frameMs);
    // Block 2: downscale only, to preprocess.target_width, aspect kept.
    const scale = Math.min(1, this.settings.target_width / vw);
    const w = Math.round(vw * scale);
    const h = Math.max(1, Math.round(vh * scale));
    if (this.canvas.width !== w || this.canvas.height !== h) [this.canvas.width, this.canvas.height] = [w, h];
    this.ctx.drawImage(this.video, 0, 0, w, h);
    const px = this.ctx.getImageData(0, 0, w, h).data;

    const captured = performance.now();
    this.perf.add("capture", captured - started);
    // M83: the same image for capture.frame_timeout_s is a lost camera, not a driver sitting still.
    const live = this.watch.image(captured, !this.repeat.repeated(px, w, h));
    this.setCameraLost(!live);
    if (!live) return;
    const t = frameMs / 1000;
    // Block 4 first (M67): it only needs the pixels, and its worker then runs while MediaPipe does,
    // so the answer is that much younger when a frame uses it.
    const fedYolo = this.maybeRunYolo(t, w, h); // own thread
    const nowMs = performance.now();
    if (fedYolo) this.perf.add("yolo_prep", nowMs - captured);
    // MediaPipe gets the frame's own time, the one blocks 6-12 use, not the time the loop got round
    // to it: its tracking then sees the same spacing between frames as the rules do.
    const ts = Math.max(Math.round(frameMs), this.lastTsMs + 1); // VIDEO mode: strictly increasing
    this.lastTsMs = ts;
    let faces: Float32Array[];
    let blink: number[] | null = null;
    let brow: number[] | null = null;
    if (E2E) {
      const feed = window.__dgFeed; // the test's synthetic landmarks stand in for block 3
      faces = (feed?.faces ?? []).map((f) => Float32Array.from(f));
      if (feed && faces.length) [blink, brow] = [feed.blink, feed.brow];
    } else {
      const result = this.landmarker!.detectForVideo(this.canvas, ts); // 3 (always set outside E2E)
      faces = result.faceLandmarks.map((f) => toPixels(f, w, h));
      // eyeBlink (left, right) per face in the same order as the faces, eye_blink_missing (open) when missing;
      // browOuterUp (mean of both sides) per face: raising the brows to keep the eyes open (block 7).
      if (result.faceBlendshapes?.length) {
        const score = (i: number, name: string, missing: number) =>
          result.faceBlendshapes?.[i]?.categories?.find((c) => c.categoryName === name)?.score ?? missing;
        const open = this.settings.eye_blink_missing;
        blink = faces.flatMap((_, i) => [score(i, "eyeBlinkLeft", open), score(i, "eyeBlinkRight", open)]);
        brow = faces.map((_, i) => (score(i, "browOuterUpLeft", 0) + score(i, "browOuterUpRight", 0)) / 2);
      }
    }
    const landmarksDone = performance.now();
    this.perf.add("landmarks", landmarksDone - nowMs);
    // Every face goes to Python, which picks the driver (largest until enrollment, then the enrolled one).
    const points = faces.length ? concatFaces(faces) : null;
    // Brightness and sharpness of every face, in the order of the landmarks: Python reads the
    // driver's (the largest face is a passenger's when they lean in). NaN = not measured. Without a
    // face, the brightness of the frame.
    const boxes = faces.map(bbox);
    const brightness = faces.length ? boxes.map((b) => meanLuma(px, w, h, b)) : meanLuma(px, w, h, null);
    const diff = channelDiff(px, w, h, this.settings.sample_stride);
    // Block 6 quality stage: is the image usable (covered lens, blurred face). Thresholds are Python's.
    const scene = lumaSpread(px, w, h, this.settings.sample_stride);
    const sharp = faces.length ? boxes.map((b) => sharpness(px, w, h, b) ?? NaN) : null;

    const measured = performance.now();
    this.perf.add("measure", measured - landmarksDone);

    if (this.yoloResultT != null) this.perf.add("yolo_age", (t - this.yoloResultT) * 1000);
    const frameId = this.frameId++;
    const pythonStart = performance.now();
    // "Nothing" goes over as undefined (Python's None). A JS null is a separate value there (JsNull):
    // a frame without a face used to fail on it instead of being a frame without a face.
    const json = this.py.frame(
      t, frameId, w, h, points ?? undefined, faces.length, blink ?? undefined, diff, brightness, brow ?? undefined, scene.mean, scene.std, sharp ?? undefined,
    ); // 6-13
    const state = JSON.parse(json) as HudSnapshot & { measures: Measures; error?: string; flush?: boolean };
    const done = performance.now();
    this.perf.add("python", done - pythonStart);
    this.perf.add("total", done - started);
    if (this.startup && this.startup.ms.first_frame == null) this.startup.ms.first_frame = Math.round(done - this.startup.t0);
    this.showFrame(state);
  }

  /** What Python answered for a frame, good or failed: the numbers for the camera card, then the HUD. */
  private showFrame(state: HudSnapshot & { measures: Measures; error?: string; flush?: boolean }) {
    if (state.flush) void this.flush(); // an L3 / unresponsive / no_answer event: not on the timer (M44)
    this.stats.level = state.level;
    this.stats.fps = state.fps ?? 0;
    this.stats.measures = state.measures;
    if (state.error) this.stats.lastError = state.error; // kept after recovery: what failed, where
    this.stats.enrollment = state.enrollment ?? null;
    this.show(state);
  }

  /** The HUD state from now on; the HUD hears at once of a change the driver must (M50). */
  private show(state: HudSnapshot) {
    this.snap = state;
    const key = urgentKey(state);
    if (key !== this.pushed) {
      this.pushed = key;
      this.listeners.forEach((listener) => listener(state));
    }
    if (E2E) window.__dgState = state;
  }

  /** True when this frame was handed to the YOLO worker. */
  private maybeRunYolo(t: number, w: number, h: number): boolean {
    if (!this.yolo || !this.yoloPacer.take(t, this.yoloBusy)) return false;
    const size = this.settings.phone.input_size;
    const g = letterboxGeometry(w, h, size);
    if (this.yoloCanvas.width !== size) [this.yoloCanvas.width, this.yoloCanvas.height] = [size, size];
    this.yoloCtx.fillStyle = "rgb(114,114,114)";
    this.yoloCtx.fillRect(0, 0, size, size);
    this.yoloCtx.drawImage(this.canvas, 0, 0, w, h, g.padX, g.padY, g.w, g.h);
    const input = toChw(this.yoloCtx.getImageData(0, 0, size, size).data, size);
    this.yoloBusy = true;
    this.yoloWatch.sent(performance.now());
    this.yoloGeometry = { ...g, w, h };
    const req: YoloRequest = { type: "run", input, size, t };
    this.yolo.postMessage(req, [input.buffer]);
    return true;
  }

  private yoloGeometry = { scale: 1, padX: 0, padY: 0, w: 0, h: 0 };

  private onYolo(msg: YoloResponse) {
    if (msg.type === "ready") {
      // The worker replaced a failing WebGPU session by a wasm one.
      this.yoloThreads = msg.threads;
      this.setYoloProvider(msg.provider);
      return;
    }
    this.yoloBusy = false;
    this.yoloWatch.answered(msg.type === "result");
    if (msg.type !== "result") {
      if (msg.type === "error") console.warn("[live] YOLO run failed:", msg.message);
      return;
    }
    const g = this.yoloGeometry;
    this.py.phone_output(msg.output, msg.numBoxes, g.scale, g.padX, g.padY, g.w, g.h, msg.t);
    this.yoloResultT = msg.t;
    this.perf.add("yolo", msg.ms);
    this.stats.yoloMs = this.stats.yoloMs == null ? msg.ms : 0.8 * this.stats.yoloMs + 0.2 * msg.ms;
  }

  // ------------------------------------------------------------------ block 14
  /** Thresholds changed on the dashboard during the trip (M47): Python applies them once the vehicle is parked. */
  private async pollThresholds() {
    if (!this.session) return;
    try {
      const tuned = await getWebThresholds(this.session);
      this.py.offer_thresholds(tuned.version, JSON.stringify(tuned.values));
    } catch {
      // offline: asked again on the next tick
    }
  }

  private async flush() {
    // M33: the heartbeat goes on while no frame arrives (camera lost, page in the background).
    if (!this.stopped) {
      this.py.perf(JSON.stringify(this.perfSnapshot())); // M49: goes out with the next heartbeat
      this.py.idle(performance.now() / 1000);
    }
    const beat = this.py.take_heartbeat();
    if (beat && this.session) this.heartbeatBody = beat;
    for (let body = this.py.take_batch(); body; body = this.py.take_batch()) {
      if (this.session) this.pendingBodies.push(body); // guest mode: nothing leaves the browser
    }
    // Offline for hours, or a login that expired: the oldest bodies go, as in the device's outbox.
    // Not the first one while it is on its way: the sender takes that one off itself.
    while (this.pendingBodies.length > this.settings.max_queue) {
      this.pendingBodies.splice(this.sending ? 1 : 0, 1);
      this.stats.dropped += 1;
    }
    if (!this.session || this.sending) return;
    this.sending = true;
    const timeoutMs = this.settings.send_timeout_s * 1000;
    try {
      let refused: number | null = null; // status of the last record the backend would never take
      while (this.pendingBodies.length) {
        try {
          const r = await postWebBatch(this.session, this.pendingBodies[0], timeoutMs);
          this.pendingBodies.shift();
          this.stats.sent += r.accepted;
        } catch (err) {
          const status = (err as ApiError).status;
          if (!DROP_STATUSES.includes(status)) throw err;
          // The backend will never take this content. As the device does (publisher.py): the records of
          // the batch are tried one by one, and only the one that is refused alone is dropped. Before M97
          // one bad record took up to publisher.web_batch_size good ones with it.
          const singles = splitBatch(this.pendingBodies[0]);
          if (singles.length > 1) this.pendingBodies.splice(0, 1, ...singles);
          else {
            this.pendingBodies.shift();
            this.stats.refused += 1;
            refused = status;
          }
        }
      }
      this.stats.sendError = refused == null ? null : `Máy chủ từ chối ${this.stats.refused} bản ghi (HTTP ${refused})`;
      await this.sendHeartbeat(this.session, timeoutMs);
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 401) this.stats.sendError = "Phiên đăng nhập hết hạn: sự kiện chưa được lưu";
      else this.stats.sendError = `Chưa gửi được tới ${API_URL || "máy chủ"}, sẽ thử lại`;
    }
    // After the round, whatever became of it: the batches never wait for the renewal.
    await this.keepSession(this.session, timeoutMs);
    this.sending = false;
  }

  /** The login outlives the trip (M97): the token is exchanged for a new one at the first round and
   *  then every half lifetime, long before it expires. Before, a trip longer than DG_TOKEN_TTL_MIN
   *  (60 min) lost everything after that: each batch came back 401 and the queue stood still behind it.
   *  Not reached: asked again at the next round. Already expired (401): nothing can renew it here, the
   *  batches stay queued and the driver is told. */
  private async keepSession(session: Session, timeoutMs: number) {
    if (Date.now() < this.refreshAt) return;
    try {
      const lifetimeS = await refreshSession(session, timeoutMs);
      this.refreshAt = Date.now() + (lifetimeS * 1000) / 2;
    } catch {
      // offline, or a backend older than M97 (404): the batches are still tried with the token there is
    }
  }

  /** The newest heartbeat, in a POST of its own after the batches. A failure never touches the
   *  batches: unreachable = kept for the next round (a newer one replaces it), refused = dropped. */
  private async sendHeartbeat(session: Session, timeoutMs: number) {
    const body = this.heartbeatBody;
    if (!body) return;
    try {
      await postWebBatch(session, body, timeoutMs);
    } catch (err) {
      const status = (err as ApiError).status;
      if (!status || status >= 500 || status === 401) return;
    }
    if (this.heartbeatBody === body) this.heartbeatBody = null;
  }

  /** One reading of the vehicle: the web driving controls first (#/drive paired with driveCode),
   *  else the terminal driving simulator. None: nothing is passed on, and the bridge reads parked /
   *  signal lost once the last reading is stale (M26). A paired remote that went quiet is not
   *  replaced by the local simulator: that is a lost signal. */
  private async pollSim() {
    if (this.simBusy || this.stopped) return;
    this.simBusy = true;
    const pollMs = this.settings.vehicle.poll_s * 1000;
    try {
      const remote = await fetch(`${API_URL}/api/v1/drive/${this.driveCode}`, {
        cache: "no-store",
        signal: AbortSignal.timeout(pollMs * 2),
      }).catch(() => null);
      if (remote?.ok) {
        const r = (await remote.json()) as { speed_kmh: number; turn_signal: string | null; age_s: number };
        if (r.age_s < this.settings.vehicle.stale_s && !this.stopped) this.py.vehicle_signal(Number(r.speed_kmh) || 0, r.turn_signal ?? null);
        return;
      }
      const resp = await fetch(DRIVE_SIM_URL, { cache: "no-store", signal: AbortSignal.timeout(pollMs * 2) });
      if (resp.ok) {
        const r = (await resp.json()) as { speed_kmh?: number; turn_signal?: string | null };
        if (!this.stopped) this.py.vehicle_signal(Number(r.speed_kmh) || 0, r.turn_signal ?? null);
      }
    } catch {
      // simulator not running
    } finally {
      this.simBusy = false;
    }
  }

  /** False once the camera and the loop are stopped (trip ended, or `stop`). */
  get running(): boolean {
    return !this.stopped;
  }

  /** The camera stream, for the enrollment frame of this page (shown only, in memory). */
  cameraStream(): MediaStream | null {
    return this.stream;
  }

  async stop() {
    if (this.stopped) return;
    this.stopped = true;
    window.clearInterval(this.flushTimer);
    window.clearInterval(this.configTimer);
    window.clearInterval(this.simTimer);
    window.clearInterval(this.watchTimer);
    this.stopPulling();
    // The camera goes first (M97): the last round waits for the backend, and a backend that hangs must
    // not keep the camera light on. Python stays until that round has taken its batches.
    this.stream.getTracks().forEach((t) => t.stop());
    this.video.srcObject = null;
    this.yolo?.terminate();
    this.landmarker?.close();
    await this.flush();
    this.py.destroy();
  }
}
