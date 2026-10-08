// The phone detector's worker (M88, audit A4 M10): which runtime it builds its session on, and the
// step back from WebGPU to wasm, at start and when a running WebGPU session dies. ONNX Runtime, the
// model download and the GPU adapter are fakes; the worker's own message handler is the real one.
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { YoloRequest, YoloResponse } from "./yolo.worker";

vi.mock("onnxruntime-web/ort-wasm-simd-threaded.mjs?url", () => ({ default: "wasm.mjs" }));
vi.mock("onnxruntime-web/ort-wasm-simd-threaded.wasm?url", () => ({ default: "wasm.wasm" }));
vi.mock("onnxruntime-web/ort-wasm-simd-threaded.asyncify.mjs?url", () => ({ default: "gpu.mjs" }));
vi.mock("onnxruntime-web/ort-wasm-simd-threaded.asyncify.wasm?url", () => ({ default: "gpu.wasm" }));

/** The two ONNX Runtime builds: sessions that answer until `broken`. */
const runtimes = vi.hoisted(() => {
  const make = () => {
    const state = { broken: false, cannotCreate: false, created: 0, runs: 0, released: 0 };
    const env = { wasm: {} as { wasmPaths?: unknown; numThreads?: number } };
    class Tensor {
      constructor(
        public type: string,
        public data: Float32Array,
        public dims: number[],
      ) {}
    }
    const InferenceSession = {
      create: vi.fn(async (_model: Uint8Array, _options: unknown) => {
        if (state.cannotCreate) throw new Error("no session here");
        state.created += 1;
        return {
          inputNames: ["images"],
          outputNames: ["output0"],
          run: async () => {
            if (state.broken) throw new Error("device lost");
            state.runs += 1;
            return { output0: { dims: [1, 84, 3], getData: async () => new Float32Array(84 * 3) } };
          },
          release: async () => void (state.released += 1),
        };
      }),
    };
    const reset = () => {
      Object.assign(state, { broken: false, cannotCreate: false, created: 0, runs: 0, released: 0 });
      env.wasm = {};
      InferenceSession.create.mockClear();
    };
    return { state, env, Tensor, InferenceSession, reset };
  };
  return { gpu: make(), wasm: make() };
});
vi.mock("onnxruntime-web/webgpu", () => runtimes.gpu);
vi.mock("onnxruntime-web/wasm", () => runtimes.wasm);
const { gpu: onGpu, wasm: onWasm } = runtimes;

const SIZE = 8;
const CREATE: YoloRequest = { type: "create", threads: 2, webgpu: true, forced: null, size: SIZE };
const RUN = (t: number): YoloRequest => ({ type: "run", input: new Float32Array(3 * SIZE * SIZE), size: SIZE, t });
const REAL_GPU = { isFallbackAdapter: false, info: { vendor: "apple", architecture: "metal-3" } };

let replies: YoloResponse[];
let send: (msg: YoloRequest) => Promise<void>;

/** A fresh worker (its state is the module's): adapter null = no WebGPU here. */
async function worker(adapter: object | null, isolated = true) {
  vi.resetModules();
  onGpu.reset();
  onWasm.reset();
  replies = [];
  const scope = { postMessage: (msg: YoloResponse) => void replies.push(msg), crossOriginIsolated: isolated, onmessage: null as ((e: { data: YoloRequest }) => Promise<void>) | null };
  vi.stubGlobal("self", scope);
  vi.stubGlobal("navigator", { hardwareConcurrency: 8, gpu: { requestAdapter: async () => adapter } });
  vi.stubGlobal("fetch", vi.fn(async (url: string) => ({ ok: !url.includes("missing"), status: 404, arrayBuffer: async () => new ArrayBuffer(16) })));
  await import("./yolo.worker");
  send = (msg) => scope.onmessage!({ data: msg });
  await send({ type: "init", modelUrl: "/models/yolov8n.onnx" });
}
const kinds = () => replies.map((r) => r.type);

beforeEach(() => void vi.spyOn(console, "warn").mockImplementation(() => undefined));
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("start", () => {
  it("a model that cannot be downloaded is an error, not a session", async () => {
    await worker(REAL_GPU);
    expect(replies).toEqual([{ type: "fetched" }]);
    await send({ type: "init", modelUrl: "/models/missing.onnx" });
    expect(replies.at(-1)).toEqual({ type: "error", message: "/models/missing.onnx: HTTP 404" });
  });

  it("a real GPU adapter: the session is on WebGPU, warmed up by one run, and wasm is never built", async () => {
    await worker(REAL_GPU);
    await send(CREATE);
    expect(replies.at(-1)).toEqual({ type: "ready", threads: 1, provider: "webgpu" });
    expect(onGpu.InferenceSession.create.mock.calls[0][1]).toEqual({ executionProviders: ["webgpu"] });
    expect(onGpu.env.wasm.wasmPaths).toEqual({ mjs: "gpu.mjs", wasm: "gpu.wasm" });
    expect(onGpu.state.runs).toBe(1);
    expect(onWasm.InferenceSession.create).not.toHaveBeenCalled();
  });

  it.each([
    ["no adapter", null, true],
    ["the browser's software adapter", { isFallbackAdapter: true }, true],
    ["a software renderer by name", { info: { description: "SwiftShader" } }, true],
    ["phone.web_gpu off", REAL_GPU, false],
  ])("%s: wasm with phone.num_threads threads, WebGPU is not tried", async (_name, adapter, allowed) => {
    await worker(adapter);
    await send({ ...CREATE, webgpu: allowed });
    expect(replies.at(-1)).toEqual({ type: "ready", threads: 2, provider: "wasm" });
    expect(onWasm.env.wasm.wasmPaths).toEqual({ mjs: "wasm.mjs", wasm: "wasm.wasm" });
    expect(onGpu.InferenceSession.create).not.toHaveBeenCalled();
  });

  it("a page that is not cross-origin isolated gets one wasm thread", async () => {
    await worker(null, false);
    await send(CREATE);
    expect(replies.at(-1)).toEqual({ type: "ready", threads: 1, provider: "wasm" });
  });

  it("WebGPU that cannot build its session, or fails its warm-up run: wasm instead, one answer", async () => {
    for (const how of ["cannotCreate", "broken"] as const) {
      await worker(REAL_GPU);
      onGpu.state[how] = true;
      await send(CREATE);
      expect(kinds(), how).toEqual(["fetched", "ready"]);
      expect(replies.at(-1)).toEqual({ type: "ready", threads: 2, provider: "wasm" });
    }
  });

  it("neither runtime works: an error, and the agent runs without phone detection", async () => {
    await worker(REAL_GPU);
    onGpu.state.cannotCreate = onWasm.state.cannotCreate = true;
    await send(CREATE);
    expect(replies.at(-1)).toEqual({ type: "error", message: "no session here" });
  });

  it("create before the model is there, and a run before a session, are errors", async () => {
    vi.resetModules();
    replies = [];
    const scope = { postMessage: (msg: YoloResponse) => void replies.push(msg), crossOriginIsolated: true, onmessage: null as ((e: { data: YoloRequest }) => Promise<void>) | null };
    vi.stubGlobal("self", scope);
    vi.stubGlobal("navigator", { hardwareConcurrency: 8 });
    await import("./yolo.worker");
    await scope.onmessage!({ data: RUN(1) });
    await scope.onmessage!({ data: CREATE });
    expect(replies).toEqual([
      { type: "error", message: "YOLO not loaded" },
      { type: "error", message: "YOLO model not downloaded" },
    ]);
  });
});

describe("runs", () => {
  it("a run answers with the raw output, its box count and the frame time it was asked with", async () => {
    await worker(null);
    await send(CREATE);
    await send(RUN(12.5));
    const result = replies.at(-1) as Extract<YoloResponse, { type: "result" }>;
    expect(result).toMatchObject({ type: "result", numBoxes: 3, t: 12.5 });
    expect(result.output.length).toBe(84 * 3);
    expect(result.ms).toBeGreaterThanOrEqual(0);
  });

  it("a WebGPU session that dies: that run is an error, then a wasm session takes over and answers", async () => {
    await worker(REAL_GPU);
    await send(CREATE);
    await send(RUN(1));
    onGpu.state.broken = true; // GPU process restarted, device lost
    await send(RUN(2));
    expect(kinds()).toEqual(["fetched", "ready", "result", "error", "ready"]);
    expect(replies.at(-1)).toEqual({ type: "ready", threads: 2, provider: "wasm" });
    expect(onGpu.state.released).toBe(1);
    await send(RUN(3));
    expect(replies.at(-1)).toMatchObject({ type: "result", t: 3 });
    expect(onWasm.state.runs).toBe(2); // the warm-up and this one
  });

  it("the step back is taken once: a wasm session that fails only answers with errors", async () => {
    await worker(REAL_GPU);
    await send(CREATE);
    onGpu.state.broken = true;
    await send(RUN(1));
    onWasm.state.broken = true;
    await send(RUN(2));
    await send(RUN(3));
    expect(kinds()).toEqual(["fetched", "ready", "error", "ready", "error", "error"]);
    expect(onWasm.state.created).toBe(1);
  });

  it("WebGPU dies and wasm cannot be built either: two errors, no session claimed ready", async () => {
    await worker(REAL_GPU);
    await send(CREATE);
    onGpu.state.broken = true;
    onWasm.state.cannotCreate = true;
    await send(RUN(1));
    expect(kinds()).toEqual(["fetched", "ready", "error", "error"]);
  });

  it("a session that started on wasm has nothing to step back to", async () => {
    await worker(null);
    await send(CREATE);
    onWasm.state.broken = true;
    await send(RUN(1));
    expect(kinds()).toEqual(["fetched", "ready", "error"]);
    expect(onWasm.state.created).toBe(1);
  });
});
