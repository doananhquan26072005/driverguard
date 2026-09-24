# DriverGuard - speed benchmark

- Machine: Intel64 Family 6 Model 170 Stepping 4, GenuineIntel, 18 logical cores, Windows 11
- Software: Python 3.13.13, onnxruntime 1.30.0, OpenCV 5.0.0, MediaPipe 1.0.1
- Input: synthetic noise 1280x720, 300 frames (NO FACE: MediaPipe timings are optimistic); face found in 0/300 frames; first 20 frames of each measurement are warm-up

## Main loop (blocks 2-12, YOLO on its own thread)

| YOLO model | FPS | p50 ms | p95 ms | max ms | YOLO runs/s | ≥ 15 FPS |
|---|---:|---:|---:|---:|---:|:---:|
| FP32 | 166.9 | 5.8 | 8.3 | 11.1 | 4.8 | ✅ |
| INT8 | 203.5 | 4.8 | 6.4 | 8.1 | 4.9 | ✅ |

Frames are processed back to back (no camera pacing), so FPS is the loop's capacity; a 30 FPS camera leaves the difference as headroom.

## Each block alone

| Block | mean ms | p50 ms | p95 ms | max ms | FPS alone |
|---|---:|---:|---:|---:|---:|
| 2 preprocess | 2.79 | 2.73 | 3.74 | 5.47 | 358 |
| 3 face landmarks (MediaPipe) | 4.30 | 4.09 | 6.48 | 10.01 | 233 |
| 6 features (EAR, MAR, solvePnP) | 0.00 | 0.00 | 0.00 | 0.03 | 354341 |
| 7-12 decision chain | 0.03 | 0.03 | 0.05 | 0.38 | 29379 |
| 4 YOLOv8n FP32 (2 threads) | 123.10 | 126.80 | 144.68 | 192.13 | 8 |
| 4 YOLOv8n INT8 (2 threads) | 61.30 | 62.22 | 73.80 | 210.86 | 16 |

## Models

| Model | Size (MB) |
|---|---:|
| face_landmarker.task (float16) | 3.76 |
| open_closed_eye.onnx (eye state, FP32) | 0.05 |
| yolov8n.onnx (FP32) | 12.85 |
| yolov8n_int8.onnx (INT8) | 3.61 |

INT8 vs FP32 phone detections on these frames: 0 matched (IoU ≥ 0.5), 0 only in FP32, 0 only in INT8.
No phone in these frames, so detection accuracy of INT8 is not measured here: run on a clip with a phone, and `tools/eval.py` with each model for precision / recall.
