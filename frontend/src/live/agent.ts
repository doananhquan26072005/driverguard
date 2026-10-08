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
import { ApiError, API_URL, getWebThresholds, postWebBatch, webDeviceId } from "../lib/api";
import type { HudEnrollment, HudSnapshot, Session, TripSummary, VehicleAction } from "../lib/types";
import { newDriveCode } from "../drive/sim";
import { DRIVE_SIM_URL, type FeedbackResult, type HudSource, type TripEnd } from "../hud/edge";
import {
  bbox,
  channelDiff,
  concatFaces,
  largestFace,
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
import { urgentKey } from "../hud/hudModel";
import { PerfWindow, type PerfSnapshot, type PerfTotals } from "./perf";
import { LoopWatchdog, type CameraTrack } from "./watchdog";
import type { YoloRequest, YoloResponse } from "./yolo.worker";

// Pinned versions: the Python side is tested against this Pyodide (numpy, pyyaml). No OpenCV since M45
// (11.7 MB less to download): head pose and box suppression run in numpy (edge_agent/perception/geometry.py).
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/";
const MEDIAPIPE_WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm";
const PYODIDE_PACKAGES = ["numpy", "pyyaml", "sqlite3"];
const BASE = import.meta.env.BASE_URL;
const CAMERA: MediaStreamConstraints = {
  video: { width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 30 }, facingMode: "user" },
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
  capture: { frame_timeout_s: number; reconnect_interval_s: number; camera_fps: number };
  target_width: number;
  landmarks: {
    num_faces: number;
    min_face_detection_confidence: number;
    min_face_presence_confidence: number;
    min_tracking_confidence: number;
    blendshapes: boolean;
  };
  phone: { input_size: number; target_fps: number; num_threads: number; web_gpu: boolean; gpu_target_fps: number };
  flush_interval_s: number;
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

function tripId(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `trip-${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

// One default mode (bridge scenario "sim"): speed and turn signal come from the web driving controls
// (#/drive?code=<driveCode>, relayed by the backend, M31) or else from the driving simulator
// (tools/drive_sim.py on 127.0.0.1); both polled by pollSim. None = parked at 0 km/h. Time of day =
// real clock.
const SIM_POLL_MS = 250;
// A remote reading older than this is not passed on: the vehicle signal goes stale (M26). Same as
// context.vehicle_signal_stale_s in config/thresholds.yaml.
const REMOTE_FRESH_S = 1.0;
async function loadPython(session: Session | null): Promise<{ agent: PyAgent; settings: Settings }> {
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
    FilesetResolver.forVisionTasks(MEDIAPIPE_WASM),
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

export class LiveAgent implements HudSource {
  address = "trình duyệt này";
  /** Pairing code for the web driving controls (#/drive?code=...), shown on the camera card. */
  readonly driveCode = newDriveCode();
  private snap: HudSnapshot = { connected: false, level: 0, reasons: [], alerts: [] };
  private stats: LiveStats = { level: 0, fps: 0, yoloMs: null, phoneOn: false, sent: 0, pending: 0, sendError: null, measures: null, enrollment: null, lastError: null, perf: null, totals: null, startup: null, recovery: { pulls: 0, reopens: 0 } };
  private stopped = false;
  private frameId = 0;
  private lastTsMs = -1;
  private lastVideoTime = -1;
  private yolo: Worker | null = null; // set once the detector's session is ready (attachYolo)
  private yoloThreads: number | null = null;
  private yoloProvider: YoloProvider | null = null;
  private yoloBusy = false;
  private yoloPacer: YoloPacer;
  private pendingBodies: string[] = [];
  private heartbeatBody: string | null = null; // M33: newest heartbeat not sent yet (never queued)
  private sending = false;
  private flushTimer: number | undefined;
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
  private watchTimer: number | undefined;
  private pullTimer: number | undefined; // set while a timer drives the loop
  private frameCallback: number | null = null; // the pending requestVideoFrameCallback / requestAnimationFrame
  private cameraLost = false;
  private reopening = false;
  private recovery: Recovery = { pulls: 0, reopens: 0 };

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
    const cap = settings.capture;
    this.watch = new LoopWatchdog(cap.frame_timeout_s * 1000, cap.reconnect_interval_s * 1000, performance.now());
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
  private static async loadYolo(): Promise<Worker | null> {
    const worker = new Worker(new URL("./yolo.worker.ts", import.meta.url), { type: "module" });
    const init: YoloRequest = { type: "init", modelUrl: `${BASE}models/yolov8n.onnx` };
    if ((await LiveAgent.askYolo(worker, init))?.type === "fetched") return worker;
    worker.terminate();
    return null;
  }

  /** The session: on WebGPU where phone.web_gpu allows it and a real GPU adapter exists, else on wasm
   *  with phone.num_threads threads where the page may use threads. */
  private static async createYolo(worker: Worker | null, cfg: Settings["phone"]): Promise<YoloSession | null> {
    if (!worker) return null;
    const request: YoloRequest = { type: "create", threads: cfg.num_threads, webgpu: cfg.web_gpu, forced: forced(PROVIDER_KEY), size: cfg.input_size };
    const answer = await LiveAgent.askYolo(worker, request);
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

  /** One request to the worker and its answer; null when it failed. */
  private static askYolo(worker: Worker, request: YoloRequest): Promise<YoloResponse | null> {
    return new Promise((resolve) => {
      worker.onmessage = (e: MessageEvent<YoloResponse>) => {
        if (e.data.type === "error") console.warn("[live] phone detector disabled:", e.data.message);
        resolve(e.data.type === "error" ? null : e.data);
      };
      worker.onerror = () => resolve(null);
      worker.postMessage(request);
    });
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
    this.simTimer = window.setInterval(() => void this.pollSim(), SIM_POLL_MS);
    this.watchTimer = window.setInterval(() => this.checkLoop(), (this.settings.capture.frame_timeout_s * 1000) / WATCH_LOOKS);
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
      this.setCameraLost(false);
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
    const frameMs = frameTimeMs(started, metadata, this.lastFrameMs);
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
    const t = frameMs / 1000;
    // Block 4 first (M67): it only needs the pixels, and its worker then runs while MediaPipe does,
    // so the answer is that much younger when a frame uses it.
    const fedYolo = this.maybeRunYolo(t, w, h); // own thread
    const nowMs = performance.now();
    if (fedYolo) this.perf.add("yolo_prep", nowMs - captured);
    const ts = Math.max(Math.round(nowMs), this.lastTsMs + 1); // VIDEO mode: strictly increasing
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
      // eyeBlink (left, right) per face in the same order as the faces, 0.05 = open when missing;
      // browOuterUp (mean of both sides) per face: raising the brows to keep the eyes open (block 7).
      if (result.faceBlendshapes?.length) {
        const score = (i: number, name: string, missing: number) =>
          result.faceBlendshapes?.[i]?.categories?.find((c) => c.categoryName === name)?.score ?? missing;
        blink = faces.flatMap((_, i) => [score(i, "eyeBlinkLeft", 0.05), score(i, "eyeBlinkRight", 0.05)]);
        brow = faces.map((_, i) => (score(i, "browOuterUpLeft", 0) + score(i, "browOuterUpRight", 0)) / 2);
      }
    }
    const landmarksDone = performance.now();
    this.perf.add("landmarks", landmarksDone - nowMs);
    // Every face goes to Python, which picks the driver (largest until enrollment, then the enrolled one).
    const points = faces.length ? concatFaces(faces) : null;
    // Brightness of the largest face: the driver's in nearly every frame, a cheap per-frame estimate.
    const k = largestFace(faces);
    const brightness = meanLuma(px, w, h, k >= 0 ? bbox(faces[k]) : null);
    const diff = channelDiff(px, w, h);
    // Block 6 quality stage: is the image usable (covered lens, blurred face). Thresholds are Python's.
    const scene = lumaSpread(px, w, h);
    const sharp = k >= 0 ? sharpness(px, w, h, bbox(faces[k])) : null;

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
    if (!this.session || this.sending || !(this.pendingBodies.length || this.heartbeatBody)) return;
    this.sending = true;
    try {
      while (this.pendingBodies.length) {
        const r = await postWebBatch(this.session, this.pendingBodies[0]);
        this.pendingBodies.shift();
        this.stats.sent += r.accepted;
        this.stats.sendError = null;
      }
      await this.sendHeartbeat(this.session);
    } catch (err) {
      const e = err as ApiError;
      if (e.status === 401) this.stats.sendError = "Phiên đăng nhập hết hạn: sự kiện chưa được lưu";
      else if (e.status && e.status < 500 && e.status !== 0) {
        this.pendingBodies.shift(); // the backend will never accept this batch
        this.stats.sendError = `Máy chủ từ chối (HTTP ${e.status})`;
      } else this.stats.sendError = `Chưa gửi được tới ${API_URL || "máy chủ"}, sẽ thử lại`;
    } finally {
      this.sending = false;
    }
  }

  /** The newest heartbeat, in a POST of its own after the batches. A failure never touches the
   *  batches: unreachable = kept for the next round (a newer one replaces it), refused = dropped. */
  private async sendHeartbeat(session: Session) {
    const body = this.heartbeatBody;
    if (!body) return;
    try {
      await postWebBatch(session, body);
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
    try {
      const remote = await fetch(`${API_URL}/api/v1/drive/${this.driveCode}`, {
        cache: "no-store",
        signal: AbortSignal.timeout(SIM_POLL_MS * 2),
      }).catch(() => null);
      if (remote?.ok) {
        const r = (await remote.json()) as { speed_kmh: number; turn_signal: string | null; age_s: number };
        if (r.age_s < REMOTE_FRESH_S && !this.stopped) this.py.vehicle_signal(Number(r.speed_kmh) || 0, r.turn_signal ?? null);
        return;
      }
      const resp = await fetch(DRIVE_SIM_URL, { cache: "no-store", signal: AbortSignal.timeout(SIM_POLL_MS * 2) });
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
    await this.flush();
    this.stream.getTracks().forEach((t) => t.stop());
    this.video.srcObject = null;
    this.yolo?.terminate();
    this.landmarker?.close();
    this.py.destroy();
  }
}
