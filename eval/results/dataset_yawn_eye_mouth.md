# DriverGuard - dataset evaluation: yawn_eye_mouth

Dataset: [serenaraju/yawn-eye-dataset-new](https://www.kaggle.com/datasets/serenaraju/yawn-eye-dataset-new), split `test`
Face images, yawning vs not (checks the MAR threshold of block 7).

215 images: no_yawn 109, yawn 106.
Face found (MediaPipe): no_yawn 108/109 (99.1%), yawn 104/106 (98.1%). No face = predicted negative.

## At the configured threshold (positive = `yawn`)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MAR (block 6) | ≥ 0.45 | 91.6% | 100.0% | 83.0% | 0.91 | 88 | 0 | 18 | 109 |

## Best threshold on this data, max recall + specificity (positive = `yawn`)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| MAR (block 6) | 0.23 | 98.6% | 99.0% | 98.1% | 99.1% | 0.99 |

## At the configured threshold (only the 212 images with a face)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| MAR (block 6) | ≥ 0.45 | 92.5% | 100.0% | 84.6% | 0.92 | 88 | 0 | 16 | 108 |

## Best threshold on this data, max recall + specificity (only the 212 images with a face)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| MAR (block 6) | 0.23 | 99.5% | 99.0% | 100.0% | 99.1% | 1.00 |

Still images: signals of a single frame, without the per-driver baselines and time rules of blocks 7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check with `tools/eval.py` on video before changing `config/thresholds.yaml`.
