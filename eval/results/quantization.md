# DriverGuard - quantisation table (M42)

One row per model and format: size, latency of the block alone, and the main loop with it. Sources:
[`benchmark.md`](benchmark.md) (Mac ARM, 10 cores, macOS, onnxruntime 1.30.0) and
[`benchmark_blocks_jetson_nano.md`](benchmark_blocks_jetson_nano.md) (`simulated`: the same Mac's CPU in a
Linux arm64 container capped to 4 CPUs / 4 GB, 2 threads per model; `tools/edge_sim.py --profile jetson_nano --blocks`).
Both on 300 frames of a YawDD clip with a face, no phone in view.

| Model (block) | Format | Size (MB) | In use | Alone, Mac: p50 / p95 ms | Alone, capped container (`simulated`): p50 / p95 ms | Main loop FPS, Mac | Main loop FPS, capped (`simulated`) | Accuracy |
|---|---|---:|---|---:|---:|---:|---:|---|
| `face_landmarker.task` (3) | TFLite float16, as shipped by MediaPipe | 3.76 | Yes | 5.81 / 5.95 | 6.47 / 9.30 | – | – | Not re-measured per format: only this one exists |
| `open_closed_eye.onnx` (5) | ONNX FP32 | 0.05 | Yes | 0.12 / 0.13 | 0.17 / 0.37 | – | – | `dataset_mrl_eye.md`, `dataset_fl3d.md` |
| `yolov8n.onnx` (4) | ONNX FP32 | 12.85 | Yes (default) | 16.64 / 17.16 | 55.09 / 64.10 | 151.8 | 125.6 | Phone detection: not measured at the face-camera angle (no data) |
| `yolov8n_int8.onnx` (4) | ONNX INT8 (QDQ, static, per-channel) | 3.61 | **No** | 19.56 / 19.79 | 19.31 / 21.98 | 152.2 | 128.1 | **Not measured**: the clips have no phone (0 detections in both) |

Long runs paced at 30 FPS ([`benchmark_simulated.md`](benchmark_simulated.md)): with INT8 the process used 57 % of one
core in the capped container against 93 % with FP32 (5 and 10 minutes); on the Mac 55 % against 54 %.

## Reading it

- **Size:** INT8 is 3.6 times smaller (12.85 → 3.61 MB). That is the gain that holds everywhere.
- **Speed depends on the runtime build, not only on the model.** On macOS, FP32 is the faster one (16.6 ms
  against 19.6 ms). In the Linux arm64 container with the same CPU and the same onnxruntime version, FP32 takes
  55 ms and INT8 19 ms. Why FP32 is that slow there was not investigated (different onnxruntime build / kernels
  for macOS and Linux arm64 is the likely reason, not checked). The main loop hardly notices either way: YOLO
  runs 5 times a second on its own thread.
- **Accuracy of INT8 is still unknown**, so the default stays FP32. It needs clips with a phone at the
  face-camera angle (own recordings, `tools/record_trace.py`), then `tools/eval.py run --phone-model
  models/yolov8n_int8.onnx` against FP32 on the same labels.
- **Eye CNN (46 KB):** not quantised on purpose: 0.12 ms per call, nothing to gain.
- **Not done:** onnxruntime-web (whether the wasm build runs this QDQ model); any real device.
- `simulated` numbers are not a Jetson: same CPU as the Mac, only fewer cores.
