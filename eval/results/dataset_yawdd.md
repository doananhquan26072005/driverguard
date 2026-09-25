Dataset: enider/yawdd-dataset (yawdd), clip-level labels.

# DriverGuard - accuracy evaluation

319 videos, 124.0 min of driving, match tolerance ±0 s.

| Behaviour | Episodes | Predictions | TP | FP | Dup | Precision | Recall | F1 | FP / hour | Delay p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| microsleep | 0 | 5 | 0 | 5 | 0 | 0.0% | – | – | 2.4 | – s |
| yawn | 114 | 114 | 94 | 0 | 20 | 100.0% | 82.5% | 0.90 | 0.0 | 6.8 s |
| nod | 0 | 4 | 0 | 4 | 0 | 0.0% | – | – | 1.9 | – s |
| drowsy | 0 | 0 | 0 | 0 | 0 | – | – | – | 0.0 | – s |
| phone | 0 | 0 | 0 | 0 | 0 | – | – | – | 0.0 | – s |
| off_road | 0 | 9 | 0 | 9 | 0 | 0.0% | – | – | 4.4 | – s |
| **all alerts** | 114 | 11 | 1 | 10 | 0 | 9.1% | – | – | 4.8 | 12.0 s |

TP / FP / Dup: matched episodes / predictions outside every episode / extra predictions in an already matched episode. Delay: prediction time minus episode start (negative = inside the tolerance before the labelled start). *all alerts*: every emitted alert (L1-L3) scored against every labelled episode, whatever its behaviour; recall is not meaningful there.
