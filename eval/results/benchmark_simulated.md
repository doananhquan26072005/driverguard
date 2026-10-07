# DriverGuard - long-run benchmark: runs side by side

Each row is one run of `tools/benchmark.py --duration` (the main loop, blocks 2-12, YOLO on its own thread, frames looped from RAM). Rows marked `simulated` ran in a container capped to a board's core count and memory on a development machine: an upper bound for that board, not a measurement of it (per-core speed, GPU / TensorRT and heat are not reproduced).

| Run | Where | Limits | Phone model | Min | FPS reached | Capacity (FPS) | Latency p95 (ms) | CPU mean (% of one core) | Memory peak (MB) | Memory growth (MB / h) | FPS ≥ 15 every minute |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| Mac dev, FP32 (face) | this machine | none | yolov8n.onnx | 10.0 | 29.9 | 107.1 | 10.8 | 54 | 601 | -360.2 | ✅ |
| Mac dev, FP32 (no_face) | this machine | none | yolov8n.onnx | 3.0 | 30.0 | 233.9 | 7.6 | 53 | 1084 | -1772.8 | ✅ |
| Mac dev, INT8 (face) | this machine | none | yolov8n_int8.onnx | 3.0 | 30.0 | 111.6 | 10.7 | 55 | 546 | -1282.4 | ✅ |
| container capped as jetson_nano (face) | `simulated` | 4 CPUs, 4096 MB | yolov8n.onnx | 10.0 | 29.9 | 102.7 | 11.1 | 93 | 597 | 54.8 | ✅ |
| container capped as jetson_orin_nano (face) | `simulated` | 6 CPUs, 8192 MB | yolov8n.onnx | 5.0 | 30.0 | 110.7 | 10.9 | 89 | 594 | 21.2 | ✅ |
| container capped as jetson_nano, INT8 (face) | `simulated` | 4 CPUs, 4096 MB | yolov8n_int8.onnx | 5.0 | 30.0 | 100.8 | 11.1 | 57 | 562 | 65.8 | ✅ |

---

## Run:

- Run: Mac dev, FP32; condition `face`; 10.0 min; paced at 30 FPS (a camera)
- Machine: arm, 10 logical cores, 17 GB, Darwin 27.0.0
- Limits: none seen by the process
- Software: Python 3.12.14, onnxruntime 1.30.0, OpenCV 4.11.0, MediaPipe 0.10.21; phone model yolov8n.onnx on 2 threads
- Input: /private/tmp/claude-501/-Users-doananhquan-Documents-AI-th-c-chi-n-P-135/d1a2458f-4a50-412a-89e1-8238fd1a8754/scratchpad/sim/yawdd_1_normal.avi (640x480, 300 frames), looped from RAM; face found in 17945/17945 frames

### Whole run

| FPS reached | Frame latency p50 / p95 / max (ms) | Capacity (1000 / mean ms) | CPU mean / p95 / max (% of one core) | CPU mean, share of the cores it may use | Memory start / end / peak (MB) | Memory growth (MB / h) | YOLO runs / s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 29.9 | 9.0 / 10.8 / 178.5 | 107.1 FPS | 54 / 56 / 226 | 5 % of 10 | 345 / 476 / 601 | -360.2 | 5.0 |

| Criterion | Result | Measured |
|---|:---:|---|
| FPS at least 15 in every minute | ✅ | lowest minute 29.1 FPS (paced at 30) |
| memory grows less than 20 MB / h | ✅ | -360.2 MB / h after the first minute |
| temperature | – | not available on this system (not judged) |

### Minute by minute

| Minute | FPS mean | FPS lowest second | p95 latency, worst second (ms) | CPU mean (%) | CPU max (%) | Memory (MB) | Temperature (°C) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30.0 | 28.7 | 22.6 | 52 | 55 | 578 | – |
| 2 | 30.0 | 29.9 | 11.0 | 53 | 55 | 504 | – |
| 3 | 30.0 | 29.7 | 20.8 | 52 | 54 | 507 | – |
| 4 | 30.0 | 29.8 | 12.0 | 52 | 54 | 505 | – |
| 5 | 30.0 | 29.7 | 11.6 | 52 | 55 | 504 | – |
| 6 | 30.0 | 29.8 | 13.1 | 52 | 55 | 504 | – |
| 7 | 30.0 | 29.7 | 13.0 | 52 | 55 | 504 | – |
| 8 | 29.1 | 18.6 | 66.0 | 68 | 226 | 478 | – |
| 9 | 30.0 | 29.9 | 12.4 | 54 | 58 | 475 | – |
| 10 | 30.0 | 29.8 | 12.1 | 55 | 57 | 476 | – |

CPU is this process only (MediaPipe, YOLO thread and the decision chain together), 100 % = one core. Frames are a short clip looped from RAM: no camera, no decoding, no HUD, no network.

---

## Run:

- Run: Mac dev, FP32; condition `no_face`; 3.0 min; paced at 30 FPS (a camera)
- Machine: arm, 10 logical cores, 17 GB, Darwin 27.0.0
- Limits: none seen by the process
- Software: Python 3.12.14, onnxruntime 1.30.0, OpenCV 4.11.0, MediaPipe 0.10.21; phone model yolov8n.onnx on 2 threads
- Input: synthetic noise 1280x720, 300 frames (NO FACE: MediaPipe timings are optimistic), looped from RAM; face found in 0/5398 frames

### Whole run

| FPS reached | Frame latency p50 / p95 / max (ms) | Capacity (1000 / mean ms) | CPU mean / p95 / max (% of one core) | CPU mean, share of the cores it may use | Memory start / end / peak (MB) | Memory growth (MB / h) | YOLO runs / s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30.0 | 3.6 / 7.6 / 26.8 | 233.9 FPS | 53 / 57 / 58 | 5 % of 10 | 348 / 1007 / 1084 | -1772.8 | 5.0 |

| Criterion | Result | Measured |
|---|:---:|---|
| FPS at least 15 in every minute | ✅ | lowest minute 30.0 FPS (paced at 30) |
| memory grows less than 20 MB / h | ✅ | -1772.8 MB / h after the first minute |
| temperature | – | not available on this system (not judged) |

### Minute by minute

| Minute | FPS mean | FPS lowest second | p95 latency, worst second (ms) | CPU mean (%) | CPU max (%) | Memory (MB) | Temperature (°C) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30.0 | 28.3 | 8.4 | 52 | 58 | 1076 | – |
| 2 | 30.0 | 29.8 | 7.9 | 53 | 57 | 1076 | – |
| 3 | 30.0 | 29.8 | 8.2 | 53 | 58 | 1007 | – |

CPU is this process only (MediaPipe, YOLO thread and the decision chain together), 100 % = one core. Frames are a short clip looped from RAM: no camera, no decoding, no HUD, no network.

---

## Run:

- Run: Mac dev, INT8; condition `face`; 3.0 min; paced at 30 FPS (a camera)
- Machine: arm, 10 logical cores, 17 GB, Darwin 27.0.0
- Limits: none seen by the process
- Software: Python 3.12.14, onnxruntime 1.30.0, OpenCV 4.11.0, MediaPipe 0.10.21; phone model yolov8n_int8.onnx on 2 threads
- Input: /private/tmp/claude-501/-Users-doananhquan-Documents-AI-th-c-chi-n-P-135/d1a2458f-4a50-412a-89e1-8238fd1a8754/scratchpad/sim/yawdd_1_normal.avi (640x480, 300 frames), looped from RAM; face found in 5400/5400 frames

### Whole run

| FPS reached | Frame latency p50 / p95 / max (ms) | Capacity (1000 / mean ms) | CPU mean / p95 / max (% of one core) | CPU mean, share of the cores it may use | Memory start / end / peak (MB) | Memory growth (MB / h) | YOLO runs / s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30.0 | 8.9 / 10.7 / 37.5 | 111.6 FPS | 55 / 58 / 59 | 6 % of 10 | 538 / 452 / 546 | -1282.4 | 5.0 |

| Criterion | Result | Measured |
|---|:---:|---|
| FPS at least 15 in every minute | ✅ | lowest minute 30.0 FPS (paced at 30) |
| memory grows less than 20 MB / h | ✅ | -1282.4 MB / h after the first minute |
| temperature | – | not available on this system (not judged) |

### Minute by minute

| Minute | FPS mean | FPS lowest second | p95 latency, worst second (ms) | CPU mean (%) | CPU max (%) | Memory (MB) | Temperature (°C) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30.0 | 29.7 | 12.6 | 54 | 58 | 500 | – |
| 2 | 30.0 | 29.8 | 12.5 | 55 | 58 | 500 | – |
| 3 | 30.0 | 29.7 | 25.3 | 56 | 59 | 452 | – |

CPU is this process only (MediaPipe, YOLO thread and the decision chain together), 100 % = one core. Frames are a short clip looped from RAM: no camera, no decoding, no HUD, no network.

---

## Run: (`simulated`)

- Run: container capped as jetson_nano; condition `face`; 10.0 min; paced at 30 FPS (a camera)
- Machine: aarch64, 10 logical cores, 8 GB, Linux 7.0.12-linuxkit
- Limits: 4.00 CPUs, 4096 MB (cgroup); profile `jetson_nano` (Jetson Nano: 4 x Cortex-A57, 4 GB): asked 4 CPUs, 4096 MB, 2 threads per model
- Software: Python 3.11.17, onnxruntime 1.30.0, OpenCV 5.0.0, MediaPipe 1.0.1; phone model yolov8n.onnx on 2 threads
- Input: /video/yawdd_1_normal.avi (640x480, 300 frames), looped from RAM; face found in 17924/17924 frames

### Whole run

| FPS reached | Frame latency p50 / p95 / max (ms) | Capacity (1000 / mean ms) | CPU mean / p95 / max (% of one core) | CPU mean, share of the cores it may use | Memory start / end / peak (MB) | Memory growth (MB / h) | YOLO runs / s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 29.9 | 9.2 / 11.1 / 184.0 | 102.7 FPS | 93 / 95 / 302 | 23 % of 4 | 572 / 597 / 597 | 54.8 | 5.0 |

| Criterion | Result | Measured |
|---|:---:|---|
| FPS at least 15 in every minute | ✅ | lowest minute 28.7 FPS (paced at 30) |
| memory grows less than 20 MB / h | ❌ | +54.8 MB / h after the first minute |
| temperature | – | not available on this system (not judged) |

### Minute by minute

| Minute | FPS mean | FPS lowest second | p95 latency, worst second (ms) | CPU mean (%) | CPU max (%) | Memory (MB) | Temperature (°C) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30.0 | 29.7 | 16.3 | 89 | 97 | 576 | – |
| 2 | 30.0 | 29.8 | 12.5 | 89 | 100 | 579 | – |
| 3 | 30.0 | 29.7 | 15.6 | 90 | 102 | 592 | – |
| 4 | 30.0 | 29.8 | 12.5 | 90 | 99 | 592 | – |
| 5 | 30.0 | 29.7 | 14.0 | 90 | 94 | 592 | – |
| 6 | 30.0 | 29.7 | 13.5 | 90 | 96 | 580 | – |
| 7 | 30.0 | 29.5 | 14.2 | 90 | 95 | 597 | – |
| 8 | 28.7 | 17.3 | 97.4 | 116 | 302 | 585 | – |
| 9 | 30.0 | 29.9 | 12.9 | 92 | 96 | 585 | – |
| 10 | 30.0 | 29.9 | 12.0 | 91 | 96 | 597 | – |

CPU is this process only (MediaPipe, YOLO thread and the decision chain together), 100 % = one core. Frames are a short clip looped from RAM: no camera, no decoding, no HUD, no network.
`simulated`: a container capped to the device's core count and memory on another machine. It does not reproduce the device's per-core speed, its GPU / TensorRT, or heat and throttling: an upper bound, not a measurement of the device.

---

## Run: (`simulated`)

- Run: container capped as jetson_orin_nano; condition `face`; 5.0 min; paced at 30 FPS (a camera)
- Machine: aarch64, 10 logical cores, 8 GB, Linux 7.0.12-linuxkit
- Limits: 6.00 CPUs, 8192 MB (cgroup); profile `jetson_orin_nano` (Jetson Orin Nano 8 GB: 6 x Cortex-A78AE, 8 GB): asked 6 CPUs, 8192 MB, 2 threads per model
- Software: Python 3.11.17, onnxruntime 1.30.0, OpenCV 5.0.0, MediaPipe 1.0.1; phone model yolov8n.onnx on 2 threads
- Input: /video/yawdd_1_normal.avi (640x480, 300 frames), looped from RAM; face found in 9000/9000 frames

### Whole run

| FPS reached | Frame latency p50 / p95 / max (ms) | Capacity (1000 / mean ms) | CPU mean / p95 / max (% of one core) | CPU mean, share of the cores it may use | Memory start / end / peak (MB) | Memory growth (MB / h) | YOLO runs / s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30.0 | 9.0 / 10.9 / 32.4 | 110.7 FPS | 89 / 94 / 97 | 15 % of 6 | 573 / 582 / 594 | 21.2 | 5.0 |

| Criterion | Result | Measured |
|---|:---:|---|
| FPS at least 15 in every minute | ✅ | lowest minute 30.0 FPS (paced at 30) |
| memory grows less than 20 MB / h | ❌ | +21.2 MB / h after the first minute |
| temperature | – | not available on this system (not judged) |

### Minute by minute

| Minute | FPS mean | FPS lowest second | p95 latency, worst second (ms) | CPU mean (%) | CPU max (%) | Memory (MB) | Temperature (°C) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30.0 | 29.8 | 11.4 | 88 | 93 | 577 | – |
| 2 | 30.0 | 29.8 | 10.7 | 88 | 92 | 593 | – |
| 3 | 30.0 | 29.7 | 10.8 | 88 | 94 | 582 | – |
| 4 | 30.0 | 29.7 | 12.0 | 90 | 96 | 582 | – |
| 5 | 30.0 | 29.7 | 12.4 | 90 | 97 | 582 | – |

CPU is this process only (MediaPipe, YOLO thread and the decision chain together), 100 % = one core. Frames are a short clip looped from RAM: no camera, no decoding, no HUD, no network.
`simulated`: a container capped to the device's core count and memory on another machine. It does not reproduce the device's per-core speed, its GPU / TensorRT, or heat and throttling: an upper bound, not a measurement of the device.

---

## Run: (`simulated`)

- Run: container capped as jetson_nano, INT8; condition `face`; 5.0 min; paced at 30 FPS (a camera)
- Machine: aarch64, 10 logical cores, 8 GB, Linux 7.0.12-linuxkit
- Limits: 4.00 CPUs, 4096 MB (cgroup); profile `jetson_nano` (Jetson Nano: 4 x Cortex-A57, 4 GB): asked 4 CPUs, 4096 MB, 2 threads per model
- Software: Python 3.11.17, onnxruntime 1.30.0, OpenCV 5.0.0, MediaPipe 1.0.1; phone model yolov8n_int8.onnx on 2 threads
- Input: /video/yawdd_1_normal.avi (640x480, 300 frames), looped from RAM; face found in 9000/9000 frames

### Whole run

| FPS reached | Frame latency p50 / p95 / max (ms) | Capacity (1000 / mean ms) | CPU mean / p95 / max (% of one core) | CPU mean, share of the cores it may use | Memory start / end / peak (MB) | Memory growth (MB / h) | YOLO runs / s |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 30.0 | 10.0 / 11.1 / 32.5 | 100.8 FPS | 57 / 61 / 68 | 14 % of 4 | 541 / 562 / 562 | 65.8 | 5.0 |

| Criterion | Result | Measured |
|---|:---:|---|
| FPS at least 15 in every minute | ✅ | lowest minute 30.0 FPS (paced at 30) |
| memory grows less than 20 MB / h | ❌ | +65.8 MB / h after the first minute |
| temperature | – | not available on this system (not judged) |

### Minute by minute

| Minute | FPS mean | FPS lowest second | p95 latency, worst second (ms) | CPU mean (%) | CPU max (%) | Memory (MB) | Temperature (°C) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30.0 | 29.6 | 21.7 | 58 | 68 | 544 | – |
| 2 | 30.0 | 29.8 | 11.1 | 57 | 60 | 559 | – |
| 3 | 30.0 | 29.9 | 11.3 | 57 | 60 | 549 | – |
| 4 | 30.0 | 29.9 | 12.0 | 57 | 61 | 550 | – |
| 5 | 30.0 | 29.9 | 17.4 | 58 | 65 | 562 | – |

CPU is this process only (MediaPipe, YOLO thread and the decision chain together), 100 % = one core. Frames are a short clip looped from RAM: no camera, no decoding, no HUD, no network.
`simulated`: a container capped to the device's core count and memory on another machine. It does not reproduce the device's per-core speed, its GPU / TensorRT, or heat and throttling: an upper bound, not a measurement of the device.

## Reading these runs (06/10/2026)

- Made with `tools/benchmark.py --duration` on a Mac (ARM, 10 cores) and `tools/edge_sim.py` (image of `Dockerfile.edge`: Linux arm64, MediaPipe 1.0.1, OpenCV 5.0.0; the Mac runs use MediaPipe 0.10.21, OpenCV 4.11.0, which has no linux/arm64 wheel). Combined with `tools/benchmark.py --combine`.
- Input: 300 frames of one YawDD clip (640x480, a face in every frame) looped from RAM; `no_face` is synthetic 1280x720 noise (hence its higher memory). No clip with a phone exists yet, so the `face_phone` condition was not run; YOLO costs the same per call whether or not a phone is in view.
- The `simulated` rows ran on the same Mac CPU, capped to 4 or 6 cores. They show the pipeline fits in that many cores and that much memory with room to spare; they do not show the speed of a Cortex-A57 / A78AE core, which is slower. Not a measurement of a Jetson.
- A Mac run and a container run were going at the same time (two chains in parallel), each paced at 30 FPS. The machine also went to idle sleep for a few minutes during the first two 10-minute runs (the clocks used do not advance in sleep, so durations are right; the one ~180 ms frame in each is probably the wake-up).
- Memory growth: the slope is fitted on 2 to 9 minutes of samples. The negative values on macOS are the OS trimming resident memory; the container runs read +21 to +66 MB / h, above the provisional `eval.soak_rss_growth_mb_per_h` (20), on at most 10 minutes. Too short to call it a leak or to rule one out: a run of an hour or more is still owed.
- Temperature was not readable on either system.
