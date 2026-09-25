# DriverGuard - speed benchmark

- Machine: arm, 10 logical cores, Darwin 27.0.0
- Software: Python 3.12.14, onnxruntime 1.30.0, OpenCV 4.11.0, MediaPipe 0.10.21
- Input: data/kaggle/datasets/enider/yawdd-dataset/versions/4/Dash/Dash/Female/1-FemaleNoGlasses.avi (640x480, 300 frames); face found in 300/300 frames; first 20 frames of each measurement are warm-up

## Main loop (blocks 2-12, YOLO on its own thread)

| YOLO model | FPS | p50 ms | p95 ms | max ms | YOLO runs/s | ≥ 15 FPS |
|---|---:|---:|---:|---:|---:|:---:|
| FP32 | 150.0 | 6.5 | 7.3 | 12.3 | 4.9 | ✅ |
| INT8 | 152.5 | 6.5 | 7.0 | 7.5 | 5.0 | ✅ |

Frames are processed back to back (no camera pacing), so FPS is the loop's capacity; a 30 FPS camera leaves the difference as headroom.

## Each block alone

| Block | mean ms | p50 ms | p95 ms | max ms | FPS alone |
|---|---:|---:|---:|---:|---:|
| 2 preprocess | 0.70 | 0.68 | 0.85 | 1.26 | 1423 |
| 3 face landmarks (MediaPipe) | 5.77 | 5.76 | 5.81 | 5.86 | 173 |
| 6 features (EAR, MAR, solvePnP) | 0.04 | 0.04 | 0.04 | 0.09 | 25348 |
| 5 eye-state CNN (when called) | 0.10 | 0.10 | 0.10 | 0.15 | 10378 |
| 7-12 decision chain | 0.01 | 0.01 | 0.02 | 0.23 | 77599 |
| 4 YOLOv8n FP32 (2 threads) | 18.21 | 16.73 | 20.11 | 140.63 | 55 |
| 4 YOLOv8n INT8 (2 threads) | 21.02 | 19.80 | 27.40 | 55.16 | 48 |

## Models

| Model | Size (MB) |
|---|---:|
| face_landmarker.task (float16) | 3.76 |
| open_closed_eye.onnx (eye state, FP32) | 0.05 |
| yolov8n.onnx (FP32) | 12.85 |
| yolov8n_int8.onnx (INT8) | 3.61 |

INT8 vs FP32 phone detections on these frames: 0 matched (IoU ≥ 0.5), 0 only in FP32, 0 only in INT8.
No phone in these frames, so detection accuracy of INT8 is not measured here: run on a clip with a phone, and `tools/eval.py` with each model for precision / recall.
