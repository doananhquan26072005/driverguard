Dataset: enider/yawdd-dataset (yawdd), clip-level labels, scored from traces (tools/seq_eval.py yawdd).

Blocks 5, 7-12 replayed from the traces with config/thresholds.yaml.

# DriverGuard - accuracy evaluation

319 videos, 124.0 min of driving, match tolerance ±0 s.

## Events and alerts

| Behaviour | Episodes | Predictions | TP | FP | Dup | Precision | Recall | F1 | Hours | FP / hour (95% CI) | Delay p50 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| microsleep | 0 | 4 | 0 | 4 | 0 | 0.0% | – | – | 2.07 | 1.9 (0.53–5.0) | – s |
| yawn | 114 | 114 | 94 | 0 | 20 | 100.0% | 82.5% | 0.90 | 1.45 | 0.0 (0.00–2.5) | 6.8 s |
| nod | 0 | 5 | 0 | 5 | 0 | 0.0% | – | – | 2.07 | 2.4 (0.79–5.6) | – s |
| drowsy | 0 | 0 | 0 | 0 | 0 | – | – | – | 2.07 | 0.0 (0.00–1.8) | – s |
| phone | 0 | 0 | 0 | 0 | 0 | – | – | – | 2.07 | 0.0 (0.00–1.8) | – s |
| off_road | 0 | 10 | 0 | 10 | 0 | 0.0% | – | – | 2.07 | 4.8 (2.32–8.9) | – s |
| **all alerts** | 114 | 11 | 1 | 10 | 0 | 9.1% | – | – | 1.45 | 6.9 (3.31–12.7) | 12.0 s |
| **all alerts L1** | 114 | 0 | 0 | 0 | 0 | – | – | – | 1.45 | 0.0 (0.00–2.5) | – s |
| **all alerts L2** | 114 | 10 | 1 | 9 | 0 | 10.0% | – | – | 1.45 | 6.2 (2.84–11.8) | 12.0 s |
| **all alerts L3** | 114 | 1 | 0 | 1 | 0 | 0.0% | – | – | 1.45 | 0.7 (0.02–3.8) | – s |

TP / FP / Dup: matched episodes / predictions outside every episode / extra predictions in an already matched episode. Delay: prediction time minus episode start (negative = inside the tolerance before the labelled start). *all alerts*: every emitted alert (L1-L3; then per level) scored against every labelled episode, whatever its behaviour; recall is not meaningful there. Hours: where a false positive of the row can happen (video time minus the row's episodes ± tolerance). FP / hour with an exact Poisson 95 % CI: a few false positives on little time say little, so no PRD verdict (≤ 1.0 / h) can be drawn from a CI that still spans it.

## False positives: start-up apart

The first 30 s of every video (`eval.warmup_s`: baselines and the PERCLOS window are still filling) against the rest. Same false positives and hours as above, split in two.

| Row | FP in the first 30 s | Hours | FP / hour (95% CI) | FP after | Hours | FP / hour (95% CI) |
|---|---:|---:|---:|---:|---:|---:|
| microsleep | 4 | 1.97 | 2.0 (0.55–5.2) | 0 | 0.09 | 0.0 (0.00–39.8) |
| yawn | 0 | 1.36 | 0.0 (0.00–2.7) | 0 | 0.09 | 0.0 (0.00–42.1) |
| nod | 4 | 1.97 | 2.0 (0.55–5.2) | 1 | 0.09 | 10.8 (0.27–60.0) |
| drowsy | 0 | 1.97 | 0.0 (0.00–1.9) | 0 | 0.09 | 0.0 (0.00–39.8) |
| phone | 0 | 1.97 | 0.0 (0.00–1.9) | 0 | 0.09 | 0.0 (0.00–39.8) |
| off_road | 9 | 1.97 | 4.6 (2.09–8.7) | 1 | 0.09 | 10.8 (0.27–60.0) |
| all alerts | 9 | 1.36 | 6.6 (3.02–12.5) | 1 | 0.09 | 11.4 (0.29–63.6) |
| all alerts L1 | 0 | 1.36 | 0.0 (0.00–2.7) | 0 | 0.09 | 0.0 (0.00–42.1) |
| all alerts L2 | 8 | 1.36 | 5.9 (2.54–11.6) | 1 | 0.09 | 11.4 (0.29–63.6) |
| all alerts L3 | 1 | 1.36 | 0.7 (0.02–4.1) | 0 | 0.09 | 0.0 (0.00–42.1) |

## FAR / MAR on windows

| Scored | Awake windows | FAR (95% CI) | Drowsy windows | MAR (95% CI) | Skipped |
|---|---:|---:|---:|---:|---:|
| Drowsiness, level ≥ L1 | 12 | 0.0% (0.0%–24.2%) | 1 | 100.0% (20.7%–100.0%) | 0 |
| Drowsiness, level ≥ L2 | 12 | 0.0% (0.0%–24.2%) | 1 | 100.0% (20.7%–100.0%) | 0 |
| Distraction, level ≥ L1 | 13 | 0.0% (0.0%–22.8%) | 0 | – | 0 |
| Distraction, level ≥ L2 | 13 | 0.0% (0.0%–22.8%) | 0 | – | 0 |

Windows of 10 s, not overlapping, from 30 s after each clip start (the start-up stretch is left out). Drowsy window: ≥ 50% inside a labelled episode; awake window: ≥ 50% known-awake and not touching an episode; others skipped. Predicted: the branch's risk level reaches the stated level in the window. Wilson CI; windows of one clip are correlated, so the CI is optimistic.

## Per person

106 people. False alerts: 10 in all, from 10 of them (9.4%); the 10 with the most have 10 (100.0%).
False alerts per hour across people: median 0.0, p90 0.0, highest 119.3. One person has minutes of video, so a single person's rate has a very wide CI: compare groups, not individuals.

The 5 people with the highest false-alert rate:

| Person | Videos | Hours | Alerts | False | False / hour (95% CI) | Episodes answered | False by behaviour | FAR windows |
|---|---:|---:|---:|---:|---:|---:|---|---:|
| F27-noglasses | 2 | 0.01 | 1 | 1 | 119.3 (3.02–665.0) | 0/1 | off_road 1 | – |
| M28-glasses | 3 | 0.01 | 1 | 1 | 82.4 (2.09–458.9) | 0/1 | off_road 1 | – |
| F24-noglasses | 3 | 0.01 | 1 | 1 | 82.2 (2.08–458.2) | 0/1 | off_road 1 | – |
| F32-sunglasses | 3 | 0.01 | 1 | 1 | 75.8 (1.92–422.1) | 0/1 | nod 1, off_road 1 | – |
| M31-glasses | 3 | 0.01 | 1 | 1 | 70.9 (1.79–395.0) | 0/1 | off_road 1 | – |

Yawning clips count as drowsy windows (YawDD has no other drowsiness label); a car parked, no distraction label, so distraction windows are all awake.
A person = gender + number + eyewear in the file name (the same number with and without glasses is kept apart: not checked whether it is one person).
