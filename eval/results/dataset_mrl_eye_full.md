# DriverGuard - dataset evaluation: mrl_eye_full

Dataset: [tauilabdelilah/mrl-eye-dataset](https://www.kaggle.com/datasets/tauilabdelilah/mrl-eye-dataset), split `test`
MRL Eye, larger copy with a test split (infrared eye crops). Block 5's CNN was trained on MRL, so expect optimistic numbers.

3223 images: closed 1566, open 1657.

## At the configured threshold (positive = `closed`)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| p_closed (CNN, block 5) | ≥ 0.6 | 95.4% | 91.4% | 100.0% | 0.95 | 1566 | 148 | 0 | 1509 |

## Best threshold on this data, max recall + specificity (positive = `closed`)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| p_closed (CNN, block 5) | 0.926 | 96.9% | 95.9% | 97.8% | 96.1% | 0.97 |

Still images: signals of a single frame, without the per-driver baselines and time rules of blocks 7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check with `tools/eval.py` on video before changing `config/thresholds.yaml`.
