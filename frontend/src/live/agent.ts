// In-browser agent (#/live): the device's pipeline on the user's own camera, in the page.
//   1 getUserMedia -> 2 canvas (resize, raw brightness / IR numbers) -> 3 MediaPipe Tasks JS
//   -> 4 YOLO in a worker -> 6-12 the device's Python (edge_agent/web/bridge.py) in Pyodide
//   -> 13 HUD (HudScreen via HudSource) + 14 batches posted with the user's token.
// Frames stay in this page's memory (video element + one canvas); only the numbers above reach
// Python and only metadata JSON leaves the browser.
import { FaceLandmarker, FilesetResolver } from "@mediapipe/tasks-vision";
import { ApiError, API_URL, getWebThresholds, postWebBatch, webDeviceId } from "../lib/api";
import type { HudSnapshot, Session } from "../lib/types";
import type { FeedbackResult, HudSource } from "../hud/edge";
import { bbox, channelDiff, largestFace, letterboxGeometry, meanLuma, toChw, toPixels } from "./measure";
import type { YoloRequest, YoloResponse } from "./yolo.worker";

// Pinned versions: the Python side is tested against this Pyodide (numpy, opencv-python, pyyaml).
const PYODIDE_URL = "https://cdn.jsdelivr.net/pyodide/v0.29.3/full/";
const MEDIAPIPE_WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm";
const BASE = import.meta.env.BASE_URL;

export const SCENARIOS = {
  city_day: "Trong phố, ban ngày (có dừng đèn đỏ)",
  highway_night: "Cao tốc ban đêm, đã lái gần 2 giờ",
  parked: "Xe đỗ (không cảnh báo mất tập trung)",
} as const;
export type Scenario = keyof typeof SCENARIOS;

export type Step = "camera" | "python" | "face" | "phone" | "ready";
export const STEPS: Record<Exclude<Step, "ready">, string> = {
  camera: "Mở camera",
  python: "Tải bộ xử lý Python (lần đầu khoảng 25 MB)",
  face: "Tải MediaPipe nhận diện khuôn mặt",
  phone: "Tải YOLO phát hiện điện thoại",
};

export interface LiveStats {
  level: number;
  fps: number;
  yoloMs: number | null;
  phoneOn: boolean;
  sent: number;
  pending: number;
  sendError: string | null;
  measures: Measures | null;
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
  target_width: number;
  landmarks: {
    num_faces: number;
    min_face_detection_confidence: number;
    min_face_presence_confidence: number;
    min_tracking_confidence: number;
    blendshapes: boolean;
  };
  phone: { input_size: number; target_fps: number };
  flush_interval_s: number;
  problems: string[];
}

// The few Pyodide calls used here (loaded from the CDN at run time, not bundled).
interface PyAgent {
  settings(): string;
  frame(...args: unknown[]): string;
  phone_output(...args: unknown[]): number;
  false_alarm(eventId: string): string;
  camera(lost: boolean): void;
  take_batch(): string | undefined;
  destroy(): void;
}
interface Pyodide {
  loadPackage(names: string[], opts?: { messageCallback?: (m: string) => void }): Promise<void>;
  unpackArchive(buf: ArrayBuffer, format: string, opts: { extractDir: string }): void;
  runPython(code: string): unknown;
  pyimport(name: string): { WebAgent: { callKwargs(...args: unknown[]): PyAgent } };
  toPy(obj: unknown): unknown;
}

function tripId(d = new Date()): string {
  const p = (n: number) => String(n).padStart(2, "0");
  return `trip-${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`;
}

async function loadPython(session: Session | null, scenario: Scenario): Promise<{ agent: PyAgent; settings: Settings }> {
  const mod = (await import(/* @vite-ignore */ `${PYODIDE_URL}pyodide.mjs`)) as {
    loadPyodide(o: { indexURL: string }): Promise<Pyodide>;
  };
  const py = await mod.loadPyodide({ indexURL: PYODIDE_URL });
  const [, zip, tuned] = await Promise.all([
    py.loadPackage(["numpy", "opencv-python", "pyyaml", "sqlite3"], { messageCallback: () => {} }),
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
  const agent = py.pyimport("edge_agent.web.bridge").WebAgent.callKwargs(deviceId, tripId(), {
    scenario,
    overrides,
  });
  const settings = JSON.parse(agent.settings()) as Settings;
  if (settings.problems.length) console.warn("[live] tuned thresholds ignored:", settings.problems);
  return { agent, settings };
}

export class LiveAgent implements HudSource {
  address = "trình duyệt này";
  private snap: HudSnapshot = { connected: false, level: 0, reasons: [], alerts: [] };
  private stats: LiveStats = { level: 0, fps: 0, yoloMs: null, phoneOn: false, sent: 0, pending: 0, sendError: null, measures: null };
  private stopped = false;
  private frameId = 0;
  private lastTsMs = -1;
  private lastVideoTime = -1;
  private yoloBusy = false;
  private lastYoloT = -Infinity;
  private pendingBodies: string[] = [];
  private sending = false;
  private flushTimer: number | undefined;
  private canvas = document.createElement("canvas");
  private ctx: CanvasRenderingContext2D;
  private yoloCanvas = document.createElement("canvas");
  private yoloCtx: CanvasRenderingContext2D;

  private constructor(
    private video: HTMLVideoElement,
    private stream: MediaStream,
    private py: PyAgent,
    private settings: Settings,
    private landmarker: FaceLandmarker,
    private yolo: Worker | null,
    private session: Session | null,
  ) {
    this.ctx = this.canvas.getContext("2d", { willReadFrequently: true })!;
    this.yoloCtx = this.yoloCanvas.getContext("2d", { willReadFrequently: true })!;
  }

  /** Ask for the camera, load the models, start the loop. onStep reports progress for the setup screen. */
  static async start(
    video: HTMLVideoElement,
    scenario: Scenario,
    session: Session | null,
    onStep: (s: Step) => void,
  ): Promise<LiveAgent> {
    onStep("camera");
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
      audio: false,
    });
    video.srcObject = stream;
    video.muted = true;
    video.playsInline = true;
    await video.play();
    try {
      onStep("python");
      const { agent, settings } = await loadPython(session, scenario);
      onStep("face");
      const lm = settings.landmarks;
      const fileset = await FilesetResolver.forVisionTasks(MEDIAPIPE_WASM);
      const options = {
        runningMode: "VIDEO" as const,
        numFaces: lm.num_faces,
        minFaceDetectionConfidence: lm.min_face_detection_confidence,
        minFacePresenceConfidence: lm.min_face_presence_confidence,
        minTrackingConfidence: lm.min_tracking_confidence,
        outputFaceBlendshapes: lm.blendshapes,
      };
      const modelAssetPath = `${BASE}models/face_landmarker.task`;
      let landmarker: FaceLandmarker;
      try {
        landmarker = await FaceLandmarker.createFromOptions(fileset, { baseOptions: { modelAssetPath, delegate: "GPU" }, ...options });
      } catch {
        landmarker = await FaceLandmarker.createFromOptions(fileset, { baseOptions: { modelAssetPath, delegate: "CPU" }, ...options });
      }
      onStep("phone");
      const yolo = await LiveAgent.loadYolo();
      const live = new LiveAgent(video, stream, agent, settings, landmarker, yolo, session);
      live.run();
      onStep("ready");
      return live;
    } catch (err) {
      stream.getTracks().forEach((t) => t.stop());
      throw err;
    }
  }

  /** YOLO in a worker; without it the agent still runs, phone detection off (as on the device). */
  private static async loadYolo(): Promise<Worker | null> {
    const worker = new Worker(new URL("./yolo.worker.ts", import.meta.url), { type: "module" });
    const ready = new Promise<boolean>((resolve) => {
      worker.onmessage = (e: MessageEvent<YoloResponse>) => {
        if (e.data.type === "error") console.warn("[live] phone detector disabled:", e.data.message);
        resolve(e.data.type === "ready");
      };
      worker.onerror = () => resolve(false);
    });
    const init: YoloRequest = { type: "init", modelUrl: `${BASE}models/yolov8n.onnx` };
    worker.postMessage(init);
    if (await ready) return worker;
    worker.terminate();
    return null;
  }

  // ------------------------------------------------------------------ HudSource
  async state(): Promise<HudSnapshot> {
    return this.snap;
  }

  async falseAlarm(eventId: string): Promise<FeedbackResult> {
    const r = this.py.false_alarm(eventId);
    if (r === "ok") void this.flush();
    return r === "ok" ? "recorded" : (r as FeedbackResult);
  }

  getStats(): LiveStats {
    return { ...this.stats, pending: this.pendingBodies.length };
  }

  // ------------------------------------------------------------------ loop
  private run() {
    const track = this.stream.getVideoTracks()[0];
    track?.addEventListener("ended", () => this.py.camera(true)); // camera unplugged / permission revoked
    if (this.yolo) {
      this.stats.phoneOn = true;
      this.yolo.onmessage = (e: MessageEvent<YoloResponse>) => this.onYolo(e.data);
    }
    this.flushTimer = window.setInterval(() => void this.flush(), this.settings.flush_interval_s * 1000);
    const next = () => {
      if (this.stopped) return;
      if ("requestVideoFrameCallback" in this.video) this.video.requestVideoFrameCallback(tick);
      else requestAnimationFrame(tick);
    };
    const tick = () => {
      if (this.stopped) return;
      if (this.video.readyState >= 2 && this.video.currentTime !== this.lastVideoTime) {
        this.lastVideoTime = this.video.currentTime;
        try {
          this.processFrame();
        } catch (err) {
          console.error("[live] frame failed", err);
        }
      }
      next();
    };
    next();
  }

  private processFrame() {
    const vw = this.video.videoWidth;
    const vh = this.video.videoHeight;
    if (!vw || !vh) return;
    // Block 2: downscale only, to preprocess.target_width, aspect kept.
    const scale = Math.min(1, this.settings.target_width / vw);
    const w = Math.round(vw * scale);
    const h = Math.max(1, Math.round(vh * scale));
    if (this.canvas.width !== w || this.canvas.height !== h) [this.canvas.width, this.canvas.height] = [w, h];
    this.ctx.drawImage(this.video, 0, 0, w, h);
    const px = this.ctx.getImageData(0, 0, w, h).data;

    const nowMs = performance.now();
    const t = nowMs / 1000;
    const ts = Math.max(Math.round(nowMs), this.lastTsMs + 1); // VIDEO mode: strictly increasing
    this.lastTsMs = ts;
    const result = this.landmarker.detectForVideo(this.canvas, ts); // 3
    const faces = result.faceLandmarks.map((f) => toPixels(f, w, h));
    const k = largestFace(faces);
    let points: Float32Array | null = null;
    let blink: [number, number] | null = null;
    if (k >= 0) {
      points = faces[k];
      const cats = result.faceBlendshapes?.[k]?.categories;
      const score = (name: string) => cats?.find((c) => c.categoryName === name)?.score;
      const l = score("eyeBlinkLeft");
      const r = score("eyeBlinkRight");
      if (l != null && r != null) blink = [l, r];
    }
    const brightness = meanLuma(px, w, h, points ? bbox(points) : null);
    const diff = channelDiff(px, w, h);

    this.maybeRunYolo(t, w, h); // 4, own thread
    const frameId = this.frameId++;
    const json = this.py.frame(t, frameId, w, h, points, faces.length, blink, diff, brightness); // 6-13
    const state = JSON.parse(json) as HudSnapshot & { measures: Measures };
    this.stats.level = state.level;
    this.stats.fps = state.fps ?? 0;
    this.stats.measures = state.measures;
    this.snap = state;
  }

  private maybeRunYolo(t: number, w: number, h: number) {
    const cfg = this.settings.phone;
    if (!this.yolo || this.yoloBusy || cfg.target_fps <= 0 || t - this.lastYoloT < 1 / cfg.target_fps) return;
    const size = cfg.input_size;
    const g = letterboxGeometry(w, h, size);
    if (this.yoloCanvas.width !== size) [this.yoloCanvas.width, this.yoloCanvas.height] = [size, size];
    this.yoloCtx.fillStyle = "rgb(114,114,114)";
    this.yoloCtx.fillRect(0, 0, size, size);
    this.yoloCtx.drawImage(this.canvas, 0, 0, w, h, g.padX, g.padY, g.w, g.h);
    const input = toChw(this.yoloCtx.getImageData(0, 0, size, size).data, size);
    this.yoloBusy = true;
    this.lastYoloT = t;
    this.yoloGeometry = { ...g, w, h };
    const req: YoloRequest = { type: "run", input, size, t };
    this.yolo.postMessage(req, [input.buffer]);
  }

  private yoloGeometry = { scale: 1, padX: 0, padY: 0, w: 0, h: 0 };

  private onYolo(msg: YoloResponse) {
    this.yoloBusy = false;
    if (msg.type !== "result") {
      if (msg.type === "error") console.warn("[live] YOLO run failed:", msg.message);
      return;
    }
    const g = this.yoloGeometry;
    this.py.phone_output(msg.output, msg.numBoxes, g.scale, g.padX, g.padY, g.w, g.h, msg.t);
    this.stats.yoloMs = this.stats.yoloMs == null ? msg.ms : 0.8 * this.stats.yoloMs + 0.2 * msg.ms;
  }

  // ------------------------------------------------------------------ block 14
  private async flush() {
    for (let body = this.py.take_batch(); body; body = this.py.take_batch()) {
      if (this.session) this.pendingBodies.push(body); // guest mode: nothing leaves the browser
    }
    if (!this.session || this.sending || !this.pendingBodies.length) return;
    this.sending = true;
    try {
      while (this.pendingBodies.length) {
        const r = await postWebBatch(this.session, this.pendingBodies[0]);
        this.pendingBodies.shift();
        this.stats.sent += r.accepted;
        this.stats.sendError = null;
      }
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

  async stop() {
    if (this.stopped) return;
    this.stopped = true;
    window.clearInterval(this.flushTimer);
    await this.flush();
    this.stream.getTracks().forEach((t) => t.stop());
    this.video.srcObject = null;
    this.yolo?.terminate();
    this.landmarker.close();
    this.py.destroy();
  }
}
