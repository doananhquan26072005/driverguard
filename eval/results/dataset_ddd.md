# DriverGuard - dataset evaluation: ddd

Dataset: [ismailnasri20/driver-drowsiness-dataset-ddd](https://www.kaggle.com/datasets/ismailnasri20/driver-drowsiness-dataset-ddd)
Driver Drowsiness Dataset (face crops from NTHU-DDD videos). Single frames only, so this is a proxy (eyes closed or yawning), not the temporal drowsiness branch.

3000 images: alert 1500, drowsy 1500.
Face found (MediaPipe): alert 1498/1500 (99.9%), drowsy 1496/1500 (99.7%). No face = predicted negative.

## At the configured threshold (positive = `drowsy`)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | ≤ 0.182 | 62.4% | 90.2% | 27.7% | 0.42 | 416 | 45 | 1084 | 1455 |
| p_closed (CNN, block 5) | ≥ 0.6 | 58.0% | 92.3% | 17.5% | 0.29 | 262 | 22 | 1238 | 1478 |
| MAR (block 6) | ≥ 0.6 | 50.1% | 100.0% | 0.1% | 0.00 | 2 | 0 | 1498 | 1500 |
| eyes closed or yawn (EAR / MAR) | ≥ 0 | 62.4% | 90.2% | 27.7% | 0.42 | 416 | 45 | 1084 | 1455 |

## Best threshold on this data, max recall + specificity (positive = `drowsy`)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | 0.223 | 69.6% | 80.4% | 51.9% | 87.3% | 0.63 |
| p_closed (CNN, block 5) | 5.39e-05 | 64.0% | 66.5% | 56.3% | 71.6% | 0.61 |
| MAR (block 6) | 0.134 | 51.3% | 82.0% | 3.3% | 99.3% | 0.06 |
| eyes closed or yawn (EAR / MAR) | -0.225 | 69.6% | 80.4% | 51.9% | 87.3% | 0.63 |

## At the configured threshold (only the 2994 images with a face)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | ≤ 0.182 | 62.4% | 90.2% | 27.8% | 0.43 | 416 | 45 | 1080 | 1453 |
| p_closed (CNN, block 5) | ≥ 0.6 | 58.0% | 92.3% | 17.5% | 0.29 | 262 | 22 | 1234 | 1476 |
| MAR (block 6) | ≥ 0.6 | 50.1% | 100.0% | 0.1% | 0.00 | 2 | 0 | 1494 | 1498 |
| eyes closed or yawn (EAR / MAR) | ≥ 0 | 62.4% | 90.2% | 27.8% | 0.43 | 416 | 45 | 1080 | 1453 |

## Best threshold on this data, max recall + specificity (only the 2994 images with a face)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | 0.223 | 69.7% | 80.4% | 52.0% | 87.3% | 0.63 |
| p_closed (CNN, block 5) | 5.39e-05 | 64.0% | 66.5% | 56.5% | 71.6% | 0.61 |
| MAR (block 6) | 0.134 | 51.3% | 82.0% | 3.3% | 99.3% | 0.06 |
| eyes closed or yawn (EAR / MAR) | -0.225 | 69.7% | 80.4% | 52.0% | 87.3% | 0.63 |

Still images: signals of a single frame, without the per-driver baselines and time rules of blocks 7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check with `tools/eval.py` on video before changing `config/thresholds.yaml`.
