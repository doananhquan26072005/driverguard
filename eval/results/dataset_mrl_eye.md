# DriverGuard - dataset evaluation: mrl_eye

Dataset: [prasadvpatil/mrl-dataset](https://www.kaggle.com/datasets/prasadvpatil/mrl-dataset)
MRL Eye, infrared eye crops (4000). Block 5's CNN was trained on MRL, so expect optimistic numbers.

4000 images: closed 2000, open 2000.

## At the configured threshold (positive = `closed`)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| p_closed (CNN, block 5) | ≥ 0.6 | 99.4% | 99.8% | 99.0% | 0.99 | 1979 | 4 | 21 | 1996 |

## Best threshold on this data, max recall + specificity (positive = `closed`)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| p_closed (CNN, block 5) | 0.6 | 99.4% | 99.8% | 99.0% | 99.8% | 0.99 |

Still images: signals of a single frame, without the per-driver baselines and time rules of blocks 7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check with `tools/eval.py` on video before changing `config/thresholds.yaml`.
