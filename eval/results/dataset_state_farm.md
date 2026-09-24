# DriverGuard - dataset evaluation: state_farm

Dataset: [rightway11/state-farm-distracted-driver-detection](https://www.kaggle.com/datasets/rightway11/state-farm-distracted-driver-detection), split `train`
State Farm Distracted Driver (side view). c1-c4 texting / calling are "phone"; c0 and c5-c9 (radio, drinking, reaching, make-up, passenger) are hard negatives.

2000 images: no_phone 1000, phone 1000.
Face found (MediaPipe): no_phone 445/1000 (44.5%), phone 204/1000 (20.4%). No face = predicted negative.

## At the configured threshold (positive = `phone`)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| phone in driver zone (block 4) | ≥ 0.35 | 50.0% | – | 0.0% | 0.00 | 0 | 0 | 1000 | 1000 |
| any phone (block 4) | ≥ 0.35 | 51.0% | 95.5% | 2.1% | 0.04 | 21 | 1 | 979 | 999 |

## Best threshold on this data, max recall + specificity (positive = `phone`)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| phone in driver zone (block 4) | 0.0522 | 50.7% | 70.6% | 2.4% | 99.0% | 0.05 |
| any phone (block 4) | 0.0517 | 59.4% | 80.9% | 24.6% | 94.2% | 0.38 |

## At the configured threshold (only the 649 images with a face)

| Signal | Threshold | Accuracy | Precision | Recall | F1 | TP | FP | FN | TN |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| phone in driver zone (block 4) | ≥ 0.35 | 68.6% | – | 0.0% | 0.00 | 0 | 0 | 204 | 445 |
| any phone (block 4) | ≥ 0.35 | 68.9% | 100.0% | 1.0% | 0.02 | 2 | 0 | 202 | 445 |

## Best threshold on this data, max recall + specificity (only the 649 images with a face)

| Signal | Best threshold | Accuracy | Precision | Recall | Specificity | F1 |
|---|---:|---:|---:|---:|---:|---:|
| phone in driver zone (block 4) | 0.0522 | 70.7% | 70.6% | 11.8% | 97.8% | 0.20 |
| any phone (block 4) | 0.057 | 73.2% | 72.7% | 23.5% | 96.0% | 0.36 |

## Predicted positive rate per source class

| Class | Label | n | phone in driver zone (block 4) | any phone (block 4) |
|---|---|---:|---:|---:|
| c0 | no_phone | 190 | 0.0% | 0.0% |
| c1 | phone | 245 | 0.0% | 0.0% |
| c2 | phone | 249 | 0.0% | 1.2% |
| c3 | phone | 253 | 0.0% | 2.8% |
| c4 | phone | 253 | 0.0% | 4.3% |
| c5 | no_phone | 175 | 0.0% | 0.0% |
| c6 | no_phone | 176 | 0.0% | 0.6% |
| c7 | no_phone | 149 | 0.0% | 0.0% |
| c8 | no_phone | 147 | 0.0% | 0.0% |
| c9 | no_phone | 163 | 0.0% | 0.0% |

Still images: signals of a single frame, without the per-driver baselines and time rules of blocks 7-8 (EAR uses `eye.baseline_init x eye.close_ratio`). A better threshold here is a hint to check with `tools/eval.py` on video before changing `config/thresholds.yaml`.
