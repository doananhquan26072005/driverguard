Dataset: enider/yawdd-dataset (yawdd), clip-level labels.

# DriverGuard - accuracy evaluation

319 videos, 124.0 min of driving, match tolerance ±0 s.

| Behaviour | Episodes | Predictions | TP | FP | Dup | Precision | Recall | F1 | FP / hour | Delay p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| microsleep | 0 | 6 | 0 | 6 | 0 | 0.0% | – | – | 2.9 | – s |
| yawn | 114 | 112 | 93 | 0 | 19 | 100.0% | 81.6% | 0.90 | 0.0 | 6.8 s |
| nod | 0 | 6 | 0 | 6 | 0 | 0.0% | – | – | 2.9 | – s |
| drowsy | 0 | 0 | 0 | 0 | 0 | – | – | – | 0.0 | – s |
| phone | 0 | 0 | 0 | 0 | 0 | – | – | – | 0.0 | – s |
| off_road | 0 | 8 | 0 | 8 | 0 | 0.0% | – | – | 3.9 | – s |
| **all alerts** | 114 | 11 | 2 | 9 | 0 | 18.2% | – | – | 4.4 | 16.6 s |

TP / FP / Dup: matched episodes / predictions outside every episode / extra predictions in an already matched episode. Delay: prediction time minus episode start (negative = inside the tolerance before the labelled start). *all alerts*: every emitted alert (L1-L3) scored against every labelled episode, whatever its behaviour; recall is not meaningful there.
