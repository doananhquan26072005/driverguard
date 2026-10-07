// Block 4 inference in its own thread (onnxruntime-web, the device's yolov8n.onnx), like the
// device's AsyncPhoneDetector: the camera loop never waits for it. Decoding (class filter, NMS)
// stays in Python (phone_detector.decode_yolov8), so only the raw output tensor goes back.
import * as ort from "onnxruntime-web/wasm"; // CPU (SIMD) build: the smallest runtime
// The runtime's own files, served as they are (M51). With threads, ONNX Runtime starts its thread
// workers from the script its glue code lives in: bundled into this worker that would be this file,
// and every thread would run the code below instead of the runtime's (the session never got ready).
import ortGlueUrl from "onnxruntime-web/ort-wasm-simd-threaded.mjs?url";
import ortWasmUrl from "onnxruntime-web/ort-wasm-simd-threaded.wasm?url";
import { yoloThreads } from "./gpu";

// init: download the model (runs beside the other downloads, before the settings are known);
// create: build the session with that many threads; run: one inference.
export type YoloRequest =
  | { type: "init"; modelUrl: string }
  | { type: "create"; threads: number }
  | { type: "run"; input: Float32Array; size: number; t: number };

export type YoloResponse =
  | { type: "fetched" }
  | { type: "ready"; threads: number } // wasm threads in use (1 unless the page is cross-origin isolated)
  | { type: "result"; output: Float32Array; numBoxes: number; t: number; ms: number }
  | { type: "error"; message: string };

let model: Uint8Array | null = null;
let session: ort.InferenceSession | null = null;

function reply(msg: YoloResponse, transfer: Transferable[] = []) {
  (self as unknown as Worker).postMessage(msg, transfer);
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
      if (!model) throw new Error("YOLO model not downloaded");
      ort.env.wasm.wasmPaths = { mjs: ortGlueUrl, wasm: ortWasmUrl };
      ort.env.wasm.numThreads = yoloThreads(msg.threads, self.crossOriginIsolated, navigator.hardwareConcurrency);
      session = await ort.InferenceSession.create(model, { executionProviders: ["wasm"] });
      model = null; // the session holds its own copy
      reply({ type: "ready", threads: ort.env.wasm.numThreads ?? 1 });
      return;
    }
    if (!session) throw new Error("YOLO not loaded");
    const t0 = performance.now();
    const input = new ort.Tensor("float32", msg.input, [1, 3, msg.size, msg.size]);
    const result = await session.run({ [session.inputNames[0]]: input });
    const out = result[session.outputNames[0]];
    const data = out.data as Float32Array;
    reply({ type: "result", output: data, numBoxes: out.dims[2], t: msg.t, ms: performance.now() - t0 }, [data.buffer]);
  } catch (err) {
    reply({ type: "error", message: String((err as Error).message ?? err) });
  }
};
