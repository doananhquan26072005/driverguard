# DriverGuard - dataset evaluation: drowsy_detection

Dataset: [yasharjebraeily/drowsy-detection-dataset](https://www.kaggle.com/datasets/yasharjebraeily/drowsy-detection-dataset), split `test`
Face crops, drowsy vs natural. Single frames only, so this is a proxy (eyes closed or yawning).

1483 images: alert 726, drowsy 757.
Face found (MediaPipe): alert 721/726 (99.3%), drowsy 391/757 (51.7%). No face = predicted negative.

## At the configured threshold (positive = `drowsy`)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | ≤ 0.182 | 69.6% | 97.2% | 41.6% | 0.58 | 315 | 9 | 442 | 717 |
| p_closed (CNN, block 5) | ≥ 0.6 | 54.6% | 98.8% | 11.2% | 0.20 | 85 | 1 | 672 | 725 |
| MAR (block 6) | ≥ 0.6 | 51.1% | 100.0% | 4.2% | 0.08 | 32 | 0 | 725 | 726 |
| eyes closed or yawn (EAR / MAR) | ≥ 0 | 70.1% | 97.3% | 42.5% | 0.59 | 322 | 9 | 435 | 717 |

## Best threshold on this data, max recall + specificity (positive = `drowsy`)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | 0.202 | 70.5% | 94.4% | 44.9% | 97.2% | 0.61 |
| p_closed (CNN, block 5) | 0.5 | 56.6% | 86.1% | 18.0% | 97.0% | 0.30 |
| MAR (block 6) | 0.178 | 59.1% | 80.2% | 26.3% | 93.3% | 0.40 |
| eyes closed or yawn (EAR / MAR) | -0.123 | 71.0% | 94.1% | 46.1% | 97.0% | 0.62 |

## At the configured threshold (only the 1112 images with a face)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | ≤ 0.182 | 92.4% | 97.2% | 80.6% | 0.88 | 315 | 9 | 76 | 712 |
| p_closed (CNN, block 5) | ≥ 0.6 | 72.4% | 98.8% | 21.7% | 0.36 | 85 | 1 | 306 | 720 |
| MAR (block 6) | ≥ 0.6 | 67.7% | 100.0% | 8.2% | 0.15 | 32 | 0 | 359 | 721 |
| eyes closed or yawn (EAR / MAR) | ≥ 0 | 93.0% | 97.3% | 82.4% | 0.89 | 322 | 9 | 69 | 712 |

## Best threshold on this data, max recall + specificity (only the 1112 images with a face)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| EAR (block 6) | 0.21 | 93.5% | 93.0% | 88.2% | 96.4% | 0.91 |
| p_closed (CNN, block 5) | 8.02e-05 | 70.1% | 55.7% | 73.7% | 68.2% | 0.63 |
| MAR (block 6) | 0.127 | 76.4% | 68.5% | 61.1% | 84.7% | 0.65 |
| eyes closed or yawn (EAR / MAR) | -0.123 | 94.2% | 94.1% | 89.3% | 96.9% | 0.92 |

Still images: signals of a single frame, without the per-driver baselines and time rules of blocks 7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check with `tools/eval.py` on video before changing `config/thresholds.yaml`.
