// @vitest-environment jsdom
// LiveAgent (#/live) around its loop (M88, audit A4 M10): what leaves the browser and when (block 14),
// the vehicle reading (block 10), stopping, and what the loop does when the camera or a frame fails
// (block 1). The class is the real one. Python, the camera, the canvas, the backend and the clock are
// fakes, so every case is a sequence of calls and times: no browser, no model, no image.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, postWebBatch } from "../lib/api";
import type { HudSnapshot, Session } from "../lib/types";
import { DRIVE_SIM_URL } from "../hud/edge";
import { LiveAgent } from "./agent";

vi.mock("@mediapipe/tasks-vision", () => ({ FaceLandmarker: {}, FilesetResolver: {} }));
vi.mock("../lib/api", async (original) => ({
  ...(await original<typeof import("../lib/api")>()),
  postWebBatch: vi.fn(),
  getWebThresholds: vi.fn(),
}));

const post = vi.mocked(postWebBatch);
const SESSION: Session = { token: "token", username: "an", role: "driver", driverId: "d1", expiresAt: 0 };
const FRAME_MS = 1000 / 30;
const LOOK_MS = 1000; // the loop is looked at capture.frame_timeout_s / 3 apart
// What WebAgent.settings() hands over, with the values of config/thresholds.yaml.
const SETTINGS = {
  capture: { frame_timeout_s: 3, reconnect_interval_s: 2, camera_fps: 30, frozen_stride: 8, max_frame_age_s: 1 },
  target_width: 640,
  sample_stride: 4,
  eye_blink_missing: 0.05,
  vehicle: { poll_s: 0.25, stale_s: 1 },
  landmarks: { num_faces: 2, min_face_detection_confidence: 0.5, min_face_presence_confidence: 0.5, min_tracking_confidence: 0.5, blendshapes: true },
  phone: { input_size: 640, target_fps: 2, num_threads: 2, web_gpu: true, gpu_target_fps: 10, run_timeout_s: 5, load_timeout_s: 30, restart_limit: 3 },
  flush_interval_s: 5,
  config_poll_s: 0,
  max_queue: 4, // publisher.max_queue is 10000; small here so a test can fill it
  problems: [],
};

type Snap = HudSnapshot & { measures?: unknown; flush?: boolean; error?: string };
const snap = (more: Partial<Snap> = {}): Snap => ({ connected: true, level: 0, reasons: [], alerts: [], ...more });
const alert = (id: string, level: 1 | 2 | 3 = 2) => ({ event_id: id, level, reasons: ["off_road" as const], at: 0, feedback: null });

/** edge_agent/web/bridge.py WebAgent as the page calls it: answers what the test puts in. */
function fakePython() {
  const batches: string[] = []; // what take_batch hands out, oldest first
  const beats: string[] = [];
  let answer = snap();
  let cameraLost = false;
  return {
    batches,
    beats,
    answers: (next: Snap) => void (answer = next),
    settings: vi.fn(),
    frame: vi.fn((..._args: unknown[]) => JSON.stringify(answer)),
    frame_error: vi.fn((_t: number, _error: string) => JSON.stringify({ ...answer, processing_error: true })),
    phone_output: vi.fn(() => 0),
    false_alarm: vi.fn((_id: string) => "ok"),
    camera: vi.fn((lost: boolean) => void (cameraLost = lost)),
    camera_attempts: vi.fn(),
    hud_state: vi.fn(() => JSON.stringify({ ...answer, camera_lost: cameraLost })),
    end_trip: vi.fn(() => JSON.stringify({ trip_id: "trip-1" })),
    vehicle: vi.fn((_action: string) => "ok"),
    vehicle_signal: vi.fn(),
    take_batch: vi.fn(() => batches.shift()),
    take_heartbeat: vi.fn(() => beats.shift()),
    idle: vi.fn(),
    perf: vi.fn(() => true),
    expect_phone: vi.fn(),
    offer_thresholds: vi.fn(() => true),
    destroy: vi.fn(),
  };
}

function fakeStream() {
  const track = Object.assign(new EventTarget(), { readyState: "live", muted: false, stop: vi.fn() });
  const stream = { getVideoTracks: () => [track], getTracks: () => [track] };
  return { track, stream: stream as unknown as MediaStream, end: () => void ((track.readyState = "ended"), track.dispatchEvent(new Event("ended"))) };
}

/** A video element whose frames the test hands over. `playing` false: the picture stands still. */
function fakeVideo() {
  const el = document.createElement("video");
  const state = { playing: true, stoodAt: 0 };
  let pending: ((now: number, meta: object) => void) | null = null;
  Object.defineProperty(el, "readyState", { get: () => 2 });
  Object.defineProperty(el, "videoWidth", { get: () => 64 });
  Object.defineProperty(el, "videoHeight", { get: () => 48 });
  Object.defineProperty(el, "currentTime", { get: () => (state.playing ? performance.now() / 1000 : state.stoodAt) });
  Object.assign(el, {
    play: () => Promise.resolve(),
    requestVideoFrameCallback: (cb: (now: number, meta: object) => void) => ((pending = cb), 1),
    cancelVideoFrameCallback: () => void (pending = null),
  });
  return {
    el,
    stand: () => void ((state.stoodAt = performance.now() / 1000), (state.playing = false)),
    resume: () => void (state.playing = true),
    armed: () => pending != null,
    /** The browser calls the loop with the next camera frame. */
    frame(meta: object = {}) {
      const cb = pending;
      pending = null;
      cb?.(performance.now(), meta);
    },
  };
}

// The canvas: every read gives another image unless `still` (the camera repeats one image).
const image = { still: false, n: 0 };
function pixels(w: number, h: number) {
  const px = new Uint8ClampedArray(w * h * 4);
  if (!image.still) image.n += 1;
  for (let i = 0; i < px.length; i++) px[i] = (i * 7 + image.n * 13) % 251;
  return px;
}
const context = { drawImage: vi.fn(), fillRect: vi.fn(), fillStyle: "", getImageData: (_x: number, _y: number, w: number, h: number) => ({ data: pixels(w, h) }) };

interface Inner {
  run(): void;
  flush(): Promise<void>;
  pollSim(): Promise<void>;
}

function build(opts: { session?: Session | null; landmarker?: unknown } = {}) {
  const py = fakePython();
  const camera = fakeStream();
  const video = fakeVideo();
  const landmarker = opts.landmarker ?? { detectForVideo: vi.fn(() => ({ faceLandmarks: [], faceBlendshapes: [] })), close: vi.fn() };
  const Agent = LiveAgent as unknown as new (...args: unknown[]) => LiveAgent;
  const agent = new Agent(video.el, camera.stream, py, SETTINGS, landmarker, opts.session === undefined ? SESSION : opts.session);
  return { agent, inner: agent as unknown as Inner, py, camera, video, landmarker: landmarker as { detectForVideo: ReturnType<typeof vi.fn>; close: ReturnType<typeof vi.fn> } };
}

/** `ms` of frames 1 / 30 s apart, each handed over by the browser's callback. */
async function frames(video: ReturnType<typeof fakeVideo>, ms: number) {
  for (let t = 0; t < ms; t += FRAME_MS) {
    await vi.advanceTimersByTimeAsync(FRAME_MS);
    video.frame();
  }
}

function deferred<T>() {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => ((resolve = res), (reject = rej)));
  return { promise, resolve, reject };
}

const getUserMedia = vi.fn();
const fetchMock = vi.fn();

beforeEach(() => {
  vi.useFakeTimers();
  image.still = false;
  post.mockReset().mockResolvedValue({ accepted: 1 });
  getUserMedia.mockReset().mockRejectedValue(new Error("no camera"));
  fetchMock.mockReset().mockRejectedValue(new Error("offline"));
  vi.stubGlobal("fetch", fetchMock);
  Object.defineProperty(navigator, "mediaDevices", { value: { getUserMedia }, configurable: true });
  vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(context as unknown as CanvasRenderingContext2D);
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------- block 14: sending
describe("flush", () => {
  it("sends the batches in the order Python made them, then the heartbeat in a request of its own", async () => {
    const { agent, inner, py } = build();
    py.batches.push("b1", "b2");
    py.beats.push("beat");
    post.mockResolvedValueOnce({ accepted: 3 }).mockResolvedValueOnce({ accepted: 2 });
    await inner.flush();
    expect(post.mock.calls.map((c) => c[1])).toEqual(["b1", "b2", "beat"]);
    expect(post.mock.calls.every((c) => c[0] === SESSION)).toBe(true);
    // The heartbeat is not counted as events.
    expect(agent.getStats()).toMatchObject({ sent: 5, pending: 0, sendError: null });
  });

  it("guest mode: Python's batches are taken and dropped, nothing leaves the browser", async () => {
    const { agent, inner, py } = build({ session: null });
    py.batches.push("b1", "b2");
    py.beats.push("beat");
    await inner.flush();
    expect(post).not.toHaveBeenCalled();
    expect(py.batches).toEqual([]);
    expect(agent.getStats()).toMatchObject({ sent: 0, pending: 0, sendError: null });
  });

  it("tells Python that time passes and hands it the loop timings before taking the heartbeat", async () => {
    const { inner, py } = build();
    await inner.flush();
    expect(py.idle).toHaveBeenCalledWith(performance.now() / 1000);
    expect(JSON.parse(py.perf.mock.calls[0][0 as never] as string)).toHaveProperty("yolo_provider");
    expect(py.perf.mock.invocationCallOrder[0]).toBeLessThan(py.take_heartbeat.mock.invocationCallOrder[0]);
  });

  it("backend unreachable or failing (no status, 5xx): everything is kept, in order, and sent later", async () => {
    for (const status of [0, 500, 503]) {
      post.mockReset();
      const { agent, inner, py } = build();
      py.batches.push("b1", "b2");
      post.mockRejectedValueOnce(new ApiError(status, "down")).mockResolvedValue({ accepted: 1 });
      await inner.flush();
      expect(agent.getStats()).toMatchObject({ sent: 0, pending: 2 });
      expect(agent.getStats().sendError).toMatch(/^Chưa gửi được/);
      await inner.flush();
      expect(post.mock.calls.map((c) => c[1])).toEqual(["b1", "b1", "b2"]);
      expect(agent.getStats()).toMatchObject({ sent: 2, pending: 0, sendError: null });
    }
  });

  it("a batch the backend refuses (4xx) is dropped whole and the next one waits for the next round", async () => {
    // Audit A4 M1: the device splits a refused batch into its records (publisher.py); the page drops
    // up to publisher.web_batch_size records with one bad one. Pinned as it is, not as it should be.
    const { agent, inner, py } = build();
    py.batches.push("bad", "good");
    post.mockRejectedValueOnce(new ApiError(422, "drowsy_score: NaN")).mockResolvedValue({ accepted: 4 });
    await inner.flush();
    expect(post).toHaveBeenCalledTimes(1);
    expect(agent.getStats()).toMatchObject({ sent: 0, pending: 1, sendError: "Máy chủ từ chối (HTTP 422)" });
    await inner.flush();
    expect(post.mock.calls.map((c) => c[1])).toEqual(["bad", "good"]);
    expect(agent.getStats()).toMatchObject({ sent: 4, pending: 0, sendError: null });
  });

  it("an expired login (401) keeps the batch, says so, and every later batch queues up behind it", async () => {
    // Audit A4 H2: the token lasts DG_TOKEN_TTL_MIN; after that nothing of the trip reaches the backend.
    const { agent, inner, py } = build();
    post.mockRejectedValue(new ApiError(401, "expired"));
    for (const body of ["b1", "b2", "b3"]) {
      py.batches.push(body);
      await inner.flush();
    }
    expect(post.mock.calls.map((c) => c[1])).toEqual(["b1", "b1", "b1"]);
    expect(agent.getStats()).toMatchObject({ sent: 0, pending: 3, sendError: "Phiên đăng nhập hết hạn: sự kiện chưa được lưu" });
  });

  it("a queue over publisher.max_queue loses its oldest bodies, counted, never the one on its way", async () => {
    const { agent, inner, py } = build();
    post.mockRejectedValue(new ApiError(0, "offline"));
    for (let i = 1; i <= 7; i++) {
      py.batches.push(`b${i}`);
      await inner.flush();
    }
    expect(agent.getStats()).toMatchObject({ pending: SETTINGS.max_queue, dropped: 3 });
    post.mockReset().mockResolvedValue({ accepted: 1 });
    await inner.flush();
    expect(post.mock.calls.map((c) => c[1])).toEqual(["b4", "b5", "b6", "b7"]);

    const first = deferred<{ accepted: number }>();
    post.mockReset().mockReturnValueOnce(first.promise).mockResolvedValue({ accepted: 1 });
    py.batches.push("c1");
    const round = inner.flush();
    for (let i = 2; i <= 7; i++) {
      py.batches.push(`c${i}`);
      await inner.flush();
    }
    first.resolve({ accepted: 1 });
    await round;
    expect(post.mock.calls.map((c) => c[1])).toEqual(["c1", "c5", "c6", "c7"]);
  });

  it("a round that starts while one is on its way posts nothing twice", async () => {
    const { agent, inner, py } = build();
    const first = deferred<{ accepted: number }>();
    post.mockReturnValueOnce(first.promise).mockResolvedValue({ accepted: 1 });
    py.batches.push("b1");
    const round = inner.flush();
    py.batches.push("b2");
    await inner.flush(); // takes b2 from Python, sends nothing: b1 is still on its way
    expect(post).toHaveBeenCalledTimes(1);
    expect(agent.getStats().pending).toBe(2);
    first.resolve({ accepted: 1 });
    await round;
    expect(post.mock.calls.map((c) => c[1])).toEqual(["b1", "b2"]);
    expect(agent.getStats()).toMatchObject({ sent: 2, pending: 0 });
  });

  it("an unreachable backend keeps only the newest heartbeat; a refused one is dropped; neither is an error", async () => {
    const { agent, inner, py } = build();
    py.beats.push("beat-1");
    post.mockRejectedValueOnce(new ApiError(0, "offline"));
    await inner.flush();
    py.beats.push("beat-2");
    post.mockRejectedValueOnce(new ApiError(503, "busy"));
    await inner.flush();
    post.mockRejectedValueOnce(new ApiError(422, "refused"));
    await inner.flush(); // no new heartbeat: beat-2 is tried again, refused, and gone
    await inner.flush();
    expect(post.mock.calls.map((c) => c[1])).toEqual(["beat-1", "beat-2", "beat-2"]);
    expect(agent.getStats()).toMatchObject({ sent: 0, pending: 0, sendError: null });
  });

  it("a failing heartbeat never holds a batch back", async () => {
    const { agent, inner, py } = build();
    py.batches.push("b1");
    py.beats.push("beat");
    post.mockResolvedValueOnce({ accepted: 1 }).mockRejectedValueOnce(new ApiError(0, "offline"));
    await inner.flush();
    expect(agent.getStats()).toMatchObject({ sent: 1, pending: 0, sendError: null });
  });

  it("goes out every flush_interval_s once the loop runs, and at once for an urgent event (M44)", async () => {
    const { inner, py, video } = build();
    inner.run();
    py.beats.push("beat");
    await vi.advanceTimersByTimeAsync(SETTINGS.flush_interval_s * 1000 - 1);
    expect(post).not.toHaveBeenCalled();
    await vi.advanceTimersByTimeAsync(1);
    expect(post.mock.calls.map((c) => c[1])).toEqual(["beat"]);

    py.answers(snap({ level: 3, flush: true }));
    py.batches.push("l3");
    await frames(video, FRAME_MS);
    expect(post.mock.calls.map((c) => c[1])).toEqual(["beat", "l3"]);
  });
});

// ---------------------------------------------------------------------------- block 10: the vehicle
describe("pollSim", () => {
  const reply = (body: unknown, ok = true) => ({ ok, json: async () => body });
  const isRemote = (url: unknown) => String(url).includes("/api/v1/drive/");

  it("passes a fresh reading of the paired driving controls on, and does not ask the local simulator", async () => {
    const { agent, inner, py } = build();
    fetchMock.mockImplementation(async (url) => reply({ speed_kmh: 62, turn_signal: "left", age_s: 0.2 }, isRemote(url)));
    await inner.pollSim();
    expect(py.vehicle_signal.mock.calls).toEqual([[62, "left"]]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(String(fetchMock.mock.calls[0][0])).toContain(`/api/v1/drive/${agent.driveCode}`);
  });

  it("paired controls that went quiet are a lost signal: nothing is passed on, the simulator is not a stand-in", async () => {
    const { inner, py } = build();
    fetchMock.mockImplementation(async (url) => reply({ speed_kmh: 62, turn_signal: null, age_s: SETTINGS.vehicle.stale_s }, isRemote(url)));
    await inner.pollSim();
    expect(py.vehicle_signal).not.toHaveBeenCalled();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("no paired controls (404): the local driving simulator is read", async () => {
    const { inner, py } = build();
    fetchMock.mockImplementation(async (url) => (isRemote(url) ? reply({}, false) : reply({ speed_kmh: 40 })));
    await inner.pollSim();
    expect(fetchMock.mock.calls.map((c) => c[0])).toEqual([expect.stringContaining("/api/v1/drive/"), DRIVE_SIM_URL]);
    expect(py.vehicle_signal.mock.calls).toEqual([[40, null]]);
  });

  it("the backend unreachable: the local simulator is still read", async () => {
    const { inner, py } = build();
    fetchMock.mockImplementation(async (url) => {
      if (isRemote(url)) throw new Error("offline");
      return reply({ speed_kmh: 15, turn_signal: "right" });
    });
    await inner.pollSim();
    expect(py.vehicle_signal.mock.calls).toEqual([[15, "right"]]);
  });

  it("no source of speed at all: Python is never given one (it then reads parked, audit top 10 no. 1)", async () => {
    const { inner, py } = build();
    inner.run();
    await vi.advanceTimersByTimeAsync(10_000);
    expect(fetchMock.mock.calls.length).toBeGreaterThan(30); // asked on, vehicle.poll_s apart
    expect(py.vehicle_signal).not.toHaveBeenCalled();
  });

  it("a speed that is not a number reads 0", async () => {
    const { inner, py } = build();
    fetchMock.mockImplementation(async (url) => reply({ speed_kmh: "fast", age_s: 0 }, isRemote(url)));
    await inner.pollSim();
    expect(py.vehicle_signal.mock.calls).toEqual([[0, null]]);
  });

  it("does not ask again while an answer is awaited, and asks again after it", async () => {
    const { inner } = build();
    const slow = deferred<unknown>();
    fetchMock.mockReturnValueOnce(slow.promise);
    const first = inner.pollSim();
    await inner.pollSim();
    expect(fetchMock).toHaveBeenCalledTimes(1);
    slow.reject(new Error("offline"));
    await first;
    await inner.pollSim();
    expect(fetchMock.mock.calls.length).toBeGreaterThan(2);
  });

  it("an answer that arrives after the agent stopped is not handed to Python", async () => {
    const { agent, inner, py } = build();
    const slow = deferred<unknown>();
    fetchMock.mockReturnValueOnce(slow.promise);
    const poll = inner.pollSim();
    await agent.stop();
    slow.resolve(reply({ speed_kmh: 62, turn_signal: null, age_s: 0 }));
    await poll;
    expect(py.vehicle_signal).not.toHaveBeenCalled();
    await inner.pollSim();
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------- stopping
describe("stop", () => {
  it("sends what is left, then releases the camera, the models and Python, and leaves no timer behind", async () => {
    const { agent, inner, py, camera, video, landmarker } = build();
    inner.run();
    py.batches.push("last");
    py.beats.push("stopped");
    await agent.stop();
    expect(post.mock.calls.map((c) => c[1])).toEqual(["last", "stopped"]);
    expect(camera.track.stop).toHaveBeenCalledTimes(1);
    expect(video.el.srcObject).toBeNull();
    expect(landmarker.close).toHaveBeenCalledTimes(1);
    expect(py.destroy).toHaveBeenCalledTimes(1);
    expect(py.take_batch.mock.invocationCallOrder.at(-1)!).toBeLessThan(py.destroy.mock.invocationCallOrder[0]);
    expect(agent.running).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
  });

  it("the last round does not ask Python for timings or to count time: it is no longer watching", async () => {
    const { agent, py } = build();
    await agent.stop();
    expect(py.idle).not.toHaveBeenCalled();
    expect(py.perf).not.toHaveBeenCalled();
    expect(py.take_heartbeat).toHaveBeenCalledTimes(1);
  });

  it("a second stop does nothing", async () => {
    const { agent, py, camera } = build();
    await agent.stop();
    await agent.stop();
    expect(py.destroy).toHaveBeenCalledTimes(1);
    expect(camera.track.stop).toHaveBeenCalledTimes(1);
  });

  it("a frame the browser hands over after the stop is not processed and no new one is asked for", async () => {
    const { agent, inner, py, video } = build();
    inner.run();
    await frames(video, 100);
    const before = py.frame.mock.calls.length;
    expect(before).toBeGreaterThan(0);
    const late = video.frame.bind(video);
    await agent.stop();
    await vi.advanceTimersByTimeAsync(FRAME_MS);
    late();
    expect(py.frame).toHaveBeenCalledTimes(before);
    expect(video.armed()).toBe(false);
  });

  // Audit A4 M1: a POST has no time limit, and stop() waits for the last round before it lets the
  // camera go. States what is wanted; `fails` comes off with the fix.
  it.fails("lets the camera go even when the backend never answers the last round", async () => {
    const { agent, py, camera } = build();
    py.batches.push("last");
    post.mockReturnValue(new Promise(() => undefined));
    void agent.stop();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(camera.track.stop).toHaveBeenCalled();
  });
});

describe("endTrip", () => {
  it("guest: the summary stays in this browser", async () => {
    const { agent, py } = build({ session: null });
    py.batches.push("summary");
    expect(await agent.endTrip()).toEqual({ summary: { trip_id: "trip-1" }, delivery: "local" });
    expect(post).not.toHaveBeenCalled();
    expect(agent.running).toBe(false);
  });

  it("signed in: sent when the backend took everything, failed when something is left", async () => {
    const sent = build();
    sent.py.batches.push("summary");
    expect((await sent.agent.endTrip()).delivery).toBe("sent");
    expect(sent.py.destroy).toHaveBeenCalledTimes(1);

    for (const status of [0, 401, 422, 500]) {
      post.mockReset().mockRejectedValue(new ApiError(status, "no"));
      const failed = build();
      failed.py.batches.push("summary");
      expect((await failed.agent.endTrip()).delivery, `HTTP ${status}`).toBe("failed");
      expect(failed.agent.running).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------- HudSource
describe("what the HUD asks for", () => {
  it("a false alarm Python recorded goes to the backend at once; its other answers are passed through", async () => {
    const { agent, py } = build();
    py.batches.push("feedback");
    expect(await agent.falseAlarm("e1")).toBe("recorded");
    await vi.advanceTimersByTimeAsync(0);
    expect(post.mock.calls.map((c) => c[1])).toEqual(["feedback"]);
    for (const answer of ["duplicate", "expired", "unknown"]) {
      py.false_alarm.mockReturnValueOnce(answer);
      expect(await agent.falseAlarm("e1")).toBe(answer);
    }
    expect(post).toHaveBeenCalledTimes(1);
  });

  it("a driver change is sent at once; a command Python does not take is false", async () => {
    const { agent, py } = build();
    py.batches.push("driver_changed");
    expect(await agent.vehicle("change_driver")).toBe(true);
    await vi.advanceTimersByTimeAsync(0);
    expect(post).toHaveBeenCalledTimes(1);
    py.vehicle.mockReturnValueOnce("ignored");
    expect(await agent.vehicle("change_driver")).toBe(false);
    expect(post).toHaveBeenCalledTimes(1);
  });

  it("the HUD hears of a new alert in the frame that brings it, once, and not after it unsubscribed (M50)", async () => {
    const { agent, inner, py, video } = build();
    const heard: Snap[] = [];
    const unsubscribe = agent.subscribe((s) => heard.push(s));
    inner.run();
    await frames(video, 300);
    expect(heard.length).toBe(1); // the first state
    py.answers(snap({ level: 2, reasons: ["off_road"], alerts: [alert("e1")] }));
    await frames(video, FRAME_MS);
    expect(heard.length).toBe(2);
    expect(heard[1].alerts[0].event_id).toBe("e1");
    expect((await agent.state()).level).toBe(2);
    await frames(video, 300);
    expect(heard.length).toBe(2);
    unsubscribe();
    py.answers(snap({ level: 3, reasons: ["microsleep"], alerts: [alert("e2", 3)] }));
    await frames(video, FRAME_MS);
    expect(heard.length).toBe(2);
  });
});

// ---------------------------------------------------------------------------- block 1: the loop watches itself
describe("the loop", () => {
  it("measures every face and gives MediaPipe the frame's own time (M90)", async () => {
    const one = (dx: number) => Array.from({ length: 478 }, (_, i) => ({ x: dx + (i % 20) / 100, y: 0.3 + (i % 23) / 100, z: 0 }));
    const detectForVideo = vi.fn(() => ({ faceLandmarks: [one(0.1), one(0.6)], faceBlendshapes: [] }));
    const { inner, py, video } = build({ landmarker: { detectForVideo, close: vi.fn() } });
    inner.run();
    await vi.advanceTimersByTimeAsync(FRAME_MS);
    video.frame({ captureTime: performance.now() - 20 }); // taken 20 ms before the loop got to it
    const call = py.frame.mock.calls[0] as unknown[];
    const [t, , , , , faces, , , brightness, , , , sharp] = call;
    expect(faces).toBe(2);
    // Brightness and sharpness of each face, in the order of the landmarks: Python reads the driver's.
    expect(brightness).toHaveLength(2);
    expect(sharp).toHaveLength(2);
    expect((brightness as number[]).every(Number.isFinite)).toBe(true);
    // Before: the time the loop got round to the frame (20 ms later than the rules' own clock).
    expect((detectForVideo.mock.calls[0] as unknown[])[1]).toBe(Math.round((t as number) * 1000));
    expect(Math.round((t as number) * 1000)).toBe(Math.round(performance.now() - 20));
  });


  it("gives Python every new frame with its own time, and nothing for a picture that did not move on", async () => {
    const { agent, inner, py, video } = build();
    inner.run();
    await frames(video, 1000);
    const n = py.frame.mock.calls.length;
    expect(n).toBe(30);
    const times = py.frame.mock.calls.map((c) => c[0] as number);
    expect(times.every((t, i) => i === 0 || t > times[i - 1])).toBe(true);
    expect(py.frame.mock.calls.map((c) => c[1])).toEqual([...Array(n).keys()]); // frame ids
    // No face: "nothing" reaches Python as undefined (its None), never as a JS null.
    expect(py.frame.mock.calls[0].includes(null)).toBe(false);
    video.stand();
    video.frame();
    expect(py.frame).toHaveBeenCalledTimes(n);
    expect(agent.getStats().recovery).toEqual({ pulls: 0, reopens: 0, yoloRestarts: 0 });
  });

  it("the browser stops calling: after frame_timeout_s a timer pulls the frames, until the browser calls again", async () => {
    const { agent, inner, py, video } = build();
    inner.run();
    await frames(video, 500);
    const before = py.frame.mock.calls.length;
    await vi.advanceTimersByTimeAsync(SETTINGS.capture.frame_timeout_s * 1000 + 1500);
    const pulled = py.frame.mock.calls.length - before;
    expect(pulled).toBeGreaterThan(10);
    expect(agent.getStats().recovery.pulls).toBe(1);
    expect(py.camera).not.toHaveBeenCalled(); // frames came: the camera is not lost

    video.frame(); // the browser is back
    const after = py.frame.mock.calls.length;
    await vi.advanceTimersByTimeAsync(900);
    expect(py.frame).toHaveBeenCalledTimes(after);
    expect(agent.getStats().recovery.pulls).toBe(1);
  });

  it("the picture stands still and pulling brings nothing: the camera is lost and asked for again, then back", async () => {
    const { agent, inner, py, camera, video } = build();
    const heard: Snap[] = [];
    agent.subscribe((s) => heard.push(s));
    inner.run();
    await frames(video, 500);
    video.stand();
    const again = fakeStream();
    getUserMedia.mockResolvedValue(again.stream);
    // Found quiet at a look after frame_timeout_s, lost at a look after another: at most two looks late.
    await vi.advanceTimersByTimeAsync(2 * (SETTINGS.capture.frame_timeout_s * 1000 + LOOK_MS));
    expect(py.camera.mock.calls).toEqual([[true]]);
    expect(heard.at(-1)?.camera_lost).toBe(true);
    expect(py.camera_attempts).toHaveBeenCalledWith(1);
    expect(getUserMedia).toHaveBeenCalledTimes(1);
    expect(camera.track.stop).toHaveBeenCalledTimes(1); // the dead stream is let go
    expect(video.el.srcObject).toBe(again.stream);
    expect(agent.cameraStream()).toBe(again.stream);
    expect(agent.getStats().recovery.reopens).toBe(1);

    video.resume();
    py.answers(snap());
    await frames(video, 100);
    expect(py.camera.mock.calls).toEqual([[true], [false]]);
    expect(heard.at(-1)?.camera_lost).toBeFalsy();
  });

  it("a camera that ends is lost at once, and asked for every reconnect_interval_s while it stays away", async () => {
    const { agent, inner, py, camera, video } = build();
    inner.run();
    await frames(video, 500);
    video.stand();
    const askedAt: number[] = [];
    py.camera_attempts.mockImplementation(() => void askedAt.push(performance.now()));
    camera.end();
    expect(py.camera.mock.calls).toEqual([[true]]);
    await vi.advanceTimersByTimeAsync(0);
    expect(getUserMedia).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(10_000);
    expect(py.camera_attempts.mock.calls.map((c) => c[0])).toEqual([1, 2, 3, 4, 5]);
    // Never sooner than reconnect_interval_s, and late by one look at the loop at most.
    const waits = askedAt.map((t, i) => t - (askedAt[i - 1] ?? t)).slice(1);
    expect(Math.min(...waits)).toBeGreaterThanOrEqual(SETTINGS.capture.reconnect_interval_s * 1000);
    expect(Math.max(...waits)).toBeLessThanOrEqual(SETTINGS.capture.reconnect_interval_s * 1000 + LOOK_MS);
    expect(agent.getStats().recovery).toMatchObject({ reopens: 5, pulls: 0 });
    expect(agent.running).toBe(true);
    expect(py.frame_error).not.toHaveBeenCalled();
  });

  it("the camera comes back after the agent stopped: the new stream is let go, not used", async () => {
    const { agent, inner, camera, video } = build();
    inner.run();
    const asked = deferred<MediaStream>();
    getUserMedia.mockReturnValue(asked.promise);
    camera.end();
    await agent.stop();
    const late = fakeStream();
    asked.resolve(late.stream);
    await vi.advanceTimersByTimeAsync(0);
    expect(late.track.stop).toHaveBeenCalledTimes(1);
    expect(video.el.srcObject).toBeNull();
  });

  it("the same image again and again for frame_timeout_s is a lost camera, until one that differs (M83)", async () => {
    const { inner, py, video } = build();
    inner.run();
    await frames(video, 500);
    image.still = true;
    const before = py.frame.mock.calls.length;
    await frames(video, SETTINGS.capture.frame_timeout_s * 1000 + 500);
    expect(py.camera.mock.calls).toEqual([[true]]);
    const whileStill = py.frame.mock.calls.length;
    expect(whileStill - before).toBeLessThan(SETTINGS.capture.frame_timeout_s * 30 + 2); // none once it is found still
    await frames(video, 300);
    expect(py.frame).toHaveBeenCalledTimes(whileStill);
    image.still = false;
    await frames(video, 100);
    expect(py.camera.mock.calls).toEqual([[true], [false]]);
    expect(py.frame.mock.calls.length).toBeGreaterThan(whileStill);
  });

  it("a frame that fails on this side is reported to Python by its class name only, and the loop goes on (M71)", async () => {
    const boom = vi.fn((): unknown => {
      throw new TypeError("frame 640x480 of an at 10.0.0.7");
    });
    const { agent, inner, py, video } = build({ landmarker: { detectForVideo: boom, close: vi.fn() } });
    const logged = vi.spyOn(console, "error").mockImplementation(() => undefined);
    inner.run();
    await frames(video, 200);
    expect(py.frame).not.toHaveBeenCalled();
    expect(py.frame_error.mock.calls.length).toBe(boom.mock.calls.length);
    expect(py.frame_error.mock.calls.every((c) => c[1] === "TypeError" && typeof c[0] === "number")).toBe(true);
    expect((await agent.state()).processing_error).toBe(true); // what Python answered is what the HUD shows
    expect(video.armed()).toBe(true);
    expect(logged).toHaveBeenCalled();

    boom.mockImplementation(() => ({ faceLandmarks: [], faceBlendshapes: [] }));
    await frames(video, 100);
    expect(py.frame).toHaveBeenCalled();
    expect((await agent.state()).processing_error).toBeFalsy();
  });

  it("Python failing too does not stop the loop: the next frame is asked for", async () => {
    const { inner, py, video } = build();
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    py.frame.mockImplementation(() => {
      throw new Error("PythonError");
    });
    py.frame_error.mockImplementation(() => {
      throw new Error("PythonError");
    });
    inner.run();
    await frames(video, 200);
    expect(py.frame.mock.calls.length).toBeGreaterThan(3);
    expect(video.armed()).toBe(true);
  });

  it("a frame that asks for an urgent send while the page is in guest mode sends nothing", async () => {
    const { inner, py, video } = build({ session: null });
    inner.run();
    py.answers(snap({ level: 3, flush: true }));
    py.batches.push("l3");
    await frames(video, 100);
    expect(post).not.toHaveBeenCalled();
  });
});
