// Block 4 inference in its own thread (onnxruntime-web, the device's yolov8n.onnx), like the
// device's AsyncPhoneDetector: the camera loop never waits for it. Decoding (class filter, NMS)
// stays in Python (phone_detector.decode_yolov8), so only the raw output tensor goes back.
import * as ort from "onnxruntime-web/wasm"; // CPU (SIMD) build: the smallest runtime

export type YoloRequest =
  | { type: "init"; modelUrl: string }
  | { type: "run"; input: Float32Array; size: number; t: number };

export type YoloResponse =
  | { type: "ready" }
  | { type: "result"; output: Float32Array; numBoxes: number; t: number; ms: number }
  | { type: "error"; message: string };

let session: ort.InferenceSession | null = null;

function reply(msg: YoloResponse, transfer: Transferable[] = []) {
  (self as unknown as Worker).postMessage(msg, transfer);
}

self.onmessage = async (e: MessageEvent<YoloRequest>) => {
  const msg = e.data;
  try {
    if (msg.type === "init") {
      // Threads need a cross-origin isolated page; otherwise one thread (still SIMD).
      ort.env.wasm.numThreads = self.crossOriginIsolated ? Math.min(4, navigator.hardwareConcurrency || 2) : 1;
      session = await ort.InferenceSession.create(msg.modelUrl, { executionProviders: ["wasm"] });
      reply({ type: "ready" });
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
