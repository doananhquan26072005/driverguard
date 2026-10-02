Dataset: enider/yawdd-dataset (yawdd), clip-level labels, scored from traces (tools/seq_eval.py yawdd).

Blocks 5, 7-12 replayed from the traces with config/thresholds.yaml.

# DriverGuard - accuracy evaluation

319 videos, 124.0 min of driving, match tolerance ±0 s.

## Events and alerts

| Behaviour | Episodes | Predictions | TP | FP | Dup | Precision | Recall | F1 | Hours | FP / hour (95% CI) | Delay p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| microsleep | 0 | 5 | 0 | 5 | 0 | 0.0% | – | – | 2.07 | 2.4 (0.79–5.6) | – s |
| yawn | 114 | 114 | 94 | 0 | 20 | 100.0% | 82.5% | 0.90 | 1.45 | 0.0 (0.00–2.5) | 6.8 s |
| nod | 0 | 5 | 0 | 5 | 0 | 0.0% | – | – | 2.07 | 2.4 (0.79–5.6) | – s |
| drowsy | 0 | 2 | 0 | 2 | 0 | 0.0% | – | – | 2.07 | 1.0 (0.12–3.5) | – s |
| phone | 0 | 0 | 0 | 0 | 0 | – | – | – | 2.07 | 0.0 (0.00–1.8) | – s |
| off_road | 0 | 9 | 0 | 9 | 0 | 0.0% | – | – | 2.07 | 4.4 (1.99–8.3) | – s |
| **all alerts** | 114 | 12 | 2 | 10 | 0 | 16.7% | – | – | 1.45 | 6.9 (3.31–12.7) | 18.8 s |
| **all alerts L1** | 114 | 2 | 1 | 1 | 0 | 50.0% | – | – | 1.45 | 0.7 (0.02–3.8) | 25.6 s |
| **all alerts L2** | 114 | 9 | 1 | 8 | 0 | 11.1% | – | – | 1.45 | 5.5 (2.38–10.9) | 12.0 s |
| **all alerts L3** | 114 | 1 | 0 | 1 | 0 | 0.0% | – | – | 1.45 | 0.7 (0.02–3.8) | – s |

TP / FP / Dup: matched episodes / predictions outside every episode / extra predictions in an already matched episode. Delay: prediction time minus episode start (negative = inside the tolerance before the labelled start). *all alerts*: every emitted alert (L1-L3; then per level) scored against every labelled episode, whatever its behaviour; recall is not meaningful there. Hours: where a false positive of the row can happen (video time minus the row's episodes ± tolerance). FP / hour with an exact Poisson 95 % CI: a few false positives on little time say little, so no PRD verdict (≤ 1.0 / h) can be drawn from a CI that still spans it.

## FAR / MAR on windows

| Scored | Awake windows | FAR (95% CI) | Drowsy windows | MAR (95% CI) | Skipped |
|---|---:|---:|---:|---:|---:|
| Drowsiness, level ≥ L1 | 12 | 0.0% (0.0%–24.2%) | 1 | 0.0% (0.0%–79.3%) | 0 |
| Drowsiness, level ≥ L2 | 12 | 0.0% (0.0%–24.2%) | 1 | 100.0% (20.7%–100.0%) | 0 |
| Distraction, level ≥ L1 | 13 | 0.0% (0.0%–22.8%) | 0 | – | 0 |
| Distraction, level ≥ L2 | 13 | 0.0% (0.0%–22.8%) | 0 | – | 0 |

Windows of 10 s, not overlapping, from 30 s after each clip start (the start-up stretch is left out). Drowsy window: ≥ 50% inside a labelled episode; awake window: ≥ 50% known-awake and not touching an episode; others skipped. Predicted: the branch's risk level reaches the stated level in the window. Wilson CI; windows of one clip are correlated, so the CI is optimistic.

Yawning clips count as drowsy windows (YawDD has no other drowsiness label); a car parked, no distraction label, so distraction windows are all awake.
