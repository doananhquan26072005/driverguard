# DriverGuard - speed benchmark

- Machine: aarch64, 10 logical cores, Linux 7.0.12-linuxkit
- Software: Python 3.11.17, onnxruntime 1.30.0, OpenCV 5.0.0, MediaPipe 1.0.1
- Input: /video/yawdd_1_normal.avi (640x480, 300 frames); face found in 300/300 frames; first 20 frames of each measurement are warm-up

## Main loop (blocks 2-12, YOLO on its own thread)

| YOLO model | FPS | p50 ms | p95 ms | max ms | YOLO runs/s | ≥ 15 FPS |
|---|---:|---:|---:|---:|---:|:---:|
| FP32 | 125.6 | 7.7 | 9.6 | 21.3 | 4.7 | ✅ |
| INT8 | 128.1 | 7.8 | 9.2 | 10.7 | 4.8 | ✅ |

Frames are processed back to back (no camera pacing), so FPS is the loop's capacity; a 30 FPS camera leaves the difference as headroom.

## Each block alone

| Block | mean ms | p50 ms | p95 ms | max ms | FPS alone |
|---|---:|---:|---:|---:|---:|
| 2 preprocess | 0.75 | 0.73 | 0.96 | 1.29 | 1330 |
| 3 face landmarks (MediaPipe) | 7.06 | 6.47 | 9.30 | 22.24 | 142 |
| 6 features (EAR, MAR, solvePnP) | 0.09 | 0.08 | 0.11 | 0.52 | 11283 |
| 5 eye-state CNN (when called) | 0.19 | 0.17 | 0.37 | 0.90 | 5207 |
| 7-12 decision chain | 0.03 | 0.02 | 0.08 | 0.27 | 33769 |
| 4 YOLOv8n FP32 (2 threads) | 57.14 | 55.09 | 64.10 | 104.13 | 18 |
| 4 YOLOv8n INT8 (2 threads) | 19.95 | 19.31 | 21.98 | 49.19 | 50 |

## Models

| Model | Size (MB) |
|---|---:|
| face_landmarker.task (float16) | 3.76 |
| open_closed_eye.onnx (eye state, FP32) | 0.05 |
| yolov8n.onnx (FP32) | 12.85 |
| yolov8n_int8.onnx (INT8) | 3.61 |

INT8 vs FP32 phone detections on these frames: 0 matched (IoU ≥ 0.5), 0 only in FP32, 0 only in INT8.
No phone in these frames, so detection accuracy of INT8 is not measured here: run on a clip with a phone, and `tools/eval.py` with each model for precision / recall.
