// Block 4 inference in its own thread (onnxruntime-web, the device's yolov8n.onnx), like the
// device's AsyncPhoneDetector: the camera loop never waits for it. Decoding (class filter, NMS)
// stays in Python (phone_detector.decode_yolov8), so only the raw output tensor goes back.
//
// Two ways to run the same model (M67): on WebGPU where a real GPU adapter exists (16 ms a run in the
// page on the machine of eval/results/benchmark_live.md), else on wasm with threads (91 ms with two).
// The runtime of the chosen one is imported when it is known, so a machine without a GPU never downloads
// the larger WebGPU runtime. The runtimes' own files are served as they are (M51): with threads, ONNX Runtime starts
// its thread workers from the script its glue code lives in; bundled into this worker that would be this
// file, and every thread would run the code below instead of the runtime's.
import wasmGlueUrl from "onnxruntime-web/ort-wasm-simd-threaded.mjs?url";
import wasmBinaryUrl from "onnxruntime-web/ort-wasm-simd-threaded.wasm?url";
import gpuGlueUrl from "onnxruntime-web/ort-wasm-simd-threaded.asyncify.mjs?url";
import gpuBinaryUrl from "onnxruntime-web/ort-wasm-simd-threaded.asyncify.wasm?url";
import { yoloProvider, yoloThreads, type GpuAdapter, type YoloProvider } from "./gpu";

type Ort = typeof import("onnxruntime-web/wasm");
type Session = Awaited<ReturnType<Ort["InferenceSession"]["create"]>>;

// init: download the model (runs beside the other downloads, before the settings are known);
// create: build the session (threads: phone.num_threads; webgpu: phone.web_gpu; forced: a provider
// forced for a measurement; size: phone.input_size, for one warm-up run); run: one inference.
export type YoloRequest =
  | { type: "init"; modelUrl: string }
  | { type: "create"; threads: number; webgpu: boolean; forced: string | null; size: number }
  | { type: "run"; input: Float32Array; size: number; t: number };

export type YoloResponse =
  | { type: "fetched" }
  // threads: wasm threads in use (1 unless the page is cross-origin isolated). Sent again when a
  // failing WebGPU session was replaced by a wasm one.
  | { type: "ready"; threads: number; provider: YoloProvider }
  | { type: "result"; output: Float32Array; numBoxes: number; t: number; ms: number }
  | { type: "error"; message: string };

let model: Uint8Array | null = null;
let ort: Ort | null = null;
let session: Session | null = null;
let provider: YoloProvider = "wasm";
let threads = 1;
let fallback: { threads: number; size: number } | null = null; // set while a WebGPU session runs: what a wasm one would need

function reply(msg: YoloResponse, transfer: Transferable[] = []) {
  (self as unknown as Worker).postMessage(msg, transfer);
}

/** What WebGPU would run on here; null when there is no adapter (no WebGPU, no GPU, blocked). */
async function gpuAdapter(): Promise<GpuAdapter | null> {
  try {
    // Not in TypeScript's DOM types of this project: only the two things read here.
    const gpu = (navigator as unknown as { gpu?: { requestAdapter(): Promise<{ isFallbackAdapter?: boolean; info?: Record<string, unknown> } | null> } }).gpu;
    const adapter = await gpu?.requestAdapter();
    if (!adapter) return null;
    const info = adapter.info ?? {};
    return {
      fallback: Boolean(adapter.isFallbackAdapter ?? info.isFallbackAdapter),
      name: [info.vendor, info.architecture, info.device, info.description].filter(Boolean).join(" "),
    };
  } catch {
    return null;
  }
}

async function run(input: Float32Array, size: number): Promise<{ data: Float32Array; numBoxes: number }> {
  if (!ort || !session) throw new Error("YOLO not loaded");
  const result = await session.run({ [session.inputNames[0]]: new ort.Tensor("float32", input, [1, 3, size, size]) });
  const out = result[session.outputNames[0]];
  return { data: (await out.getData()) as Float32Array, numBoxes: out.dims[2] };
}

/** Session on `want`, warmed up by one run (WebGPU compiles its shaders on the first one: 0.5 s). */
async function create(want: YoloProvider, wantedThreads: number, size: number): Promise<void> {
  if (!model) throw new Error("YOLO model not downloaded");
  const gpu = want === "webgpu";
  const runtime: Ort = gpu ? ((await import("onnxruntime-web/webgpu")) as unknown as Ort) : await import("onnxruntime-web/wasm");
  runtime.env.wasm.wasmPaths = gpu ? { mjs: gpuGlueUrl, wasm: gpuBinaryUrl } : { mjs: wasmGlueUrl, wasm: wasmBinaryUrl };
  runtime.env.wasm.numThreads = gpu ? 1 : yoloThreads(wantedThreads, self.crossOriginIsolated, navigator.hardwareConcurrency);
  // A copy: the runtime may take the buffer over, and a wasm session may still have to follow a failed WebGPU one.
  const made = await runtime.InferenceSession.create(model.slice(), { executionProviders: [want] });
  [ort, session, provider, threads] = [runtime, made, want, runtime.env.wasm.numThreads ?? 1];
  await run(new Float32Array(3 * size * size), size);
}

self.onmessage = async (e: MessageEvent<YoloRequest>) => {
  const msg = e.data;
  try {
    if (msg.type === "init") {
      const resp = await fetch(msg.modelUrl);
      if (!resp.ok) throw new Error(`${msg.modelUrl}: HTTP ${resp.status}`);
      model = new Uint8Array(await resp.arrayBuffer());
      reply({ type: "fetched" });
      return;
    }
    if (msg.type === "create") {
      const want = yoloProvider(msg.webgpu, await gpuAdapter(), msg.forced);
      try {
        await create(want, msg.threads, msg.size);
      } catch (err) {
        if (want !== "webgpu") throw err;
        console.warn("[live] phone detector: WebGPU failed, using wasm:", String((err as Error).message ?? err));
        await create("wasm", msg.threads, msg.size);
      }
      if (provider === "webgpu") fallback = { threads: msg.threads, size: msg.size };
      else model = null; // the session holds its own copy (kept beside a WebGPU session, for the fallback below)
      reply({ type: "ready", threads, provider });
      return;
    }
    const t0 = performance.now();
    const { data, numBoxes } = await run(msg.input, msg.size);
    reply({ type: "result", output: data, numBoxes, t: msg.t, ms: performance.now() - t0 }, [data.buffer]);
  } catch (err) {
    reply({ type: "error", message: String((err as Error).message ?? err) });
    // A WebGPU session that stops working (GPU process restarted, device lost): go on with wasm. Tried once.
    if (msg.type === "run" && fallback) {
      const { threads: wantedThreads, size } = fallback;
      const dead = session;
      fallback = null;
      try {
        await create("wasm", wantedThreads, size);
        model = null;
        void dead?.release().catch(() => undefined);
        reply({ type: "ready", threads, provider });
      } catch (again) {
        reply({ type: "error", message: String((again as Error).message ?? again) });
      }
    }
  }
};
