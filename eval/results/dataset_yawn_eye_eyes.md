# DriverGuard - dataset evaluation: yawn_eye_eyes

Dataset: [serenaraju/yawn-eye-dataset-new](https://www.kaggle.com/datasets/serenaraju/yawn-eye-dataset-new), split `test`
Colour eye close-ups, open vs closed.

218 images: closed 109, open 109.

## At the configured threshold (positive = `closed`)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| p_closed (CNN, block 5) | ≥ 0.6 | 88.1% | 97.7% | 78.0% | 0.87 | 85 | 2 | 24 | 107 |

## Best threshold on this data, max recall + specificity (positive = `closed`)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| p_closed (CNN, block 5) | 9.3e-05 | 90.8% | 88.7% | 93.6% | 88.1% | 0.91 |

Still images: signals of a single frame, without the per-driver baselines and time rules of blocks 7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check with `tools/eval.py` on video before changing `config/thresholds.yaml`.
