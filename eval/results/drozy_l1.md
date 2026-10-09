# DriverGuard - DROZY: risk.drowsy.l1 40 or 50, by a rule written before the run (M101)

Rule: `eval/splits/drozy_l1_rule.md`. Source: commit 2990b41 (uncommitted changes); thresholds.yaml sha256 50f7d176ce54; 1-1.pkl.gz (modified 2026-10-09).

DROZY: 14 subjects at a screen (not driving), fixed near-infrared camera, one KSS score per 10 min test. awake = KSS <= 4, drowsy = KSS >= 7; KSS 5-6 is listed apart. Blocks 7-12 replayed on per-frame numbers (no image kept) at l1 = 40 and 50 and nothing else. False alarms = drowsiness-branch alerts on awake videos after the 30 s start-up. The decision is taken on the `web` path (block 5 reads eyeBlink, as #/live); `device` (the eye CNN) is shown beside it.

## Verdict: l1 = 40

a condition of section 5 does not hold: keep 40.

| Condition | Holds |
|---|---|
| G1 reliable face, median >= 80 % | yes |
| G2 >= 1.5 h awake and >= 8 drowsy videos | yes |
| G3 AUC of the mean score >= 0.65 | yes |
| 1 false alarms at least halved and at least 3 fewer | no |
| 2 at most one drowsy video loses its alert | yes |

## The counts

| Path | l1 | Awake videos, hours | False alarms | Awake videos with one | Drowsy videos with an alert | reaching L3 | KSS 5-6 videos with an alert | AUC of the mean score | Reliable face, median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| web (decides) | 40 | 15, 2.33 h | 0 | 0 / 15 | 7 / 15 | 3 | 2 / 6 | 0.809 | 98.5 % |
| web (decides) | 50 | 15, 2.33 h | 0 | 0 / 15 | 6 / 15 | 3 | 2 / 6 | 0.809 | 98.5 % |
| device | 40 | 15, 2.33 h | 0 | 0 / 15 | 5 / 15 | 2 | 0 / 6 | 0.738 | 98.5 % |
| device | 50 | 15, 2.33 h | 0 | 0 / 15 | 5 / 15 | 2 | 0 / 6 | 0.738 | 98.5 % |

Recorded at 15 FPS (kept in every number above): 16 of 36 videos; on the `web` path at l1 = 40 they hold 0 of the 0 false alarms.

## Per video (`web` path)

| Video | KSS | Label | FPS | Reliable face | Mean drowsy_score | Drowsiness alerts at 40 | at 50 | L3 at 40 |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| 1-1 | 3 | awake | 30 | 99.3 % | 0.0 | 0 | 0 | 0 |
| 1-2 | 6 | between | 15 | 99.1 % | 0.0 | 0 | 0 | 0 |
| 1-3 | 7 | drowsy | 15 | 49.9 % | 0.8 | 0 | 0 | 0 |
| 2-1 | 3 | awake | 30 | 99.1 % | 0.0 | 0 | 0 | 0 |
| 2-2 | 7 | drowsy | 15 | 50.3 % | 4.4 | 1 | 0 | 0 |
| 2-3 | 6 | between | 15 | 100.0 % | 10.2 | 0 | 0 | 0 |
| 3-1 | 2 | awake | 30 | 99.8 % | 0.0 | 0 | 0 | 0 |
| 3-2 | 3 | awake | 15 | 49.0 % | 0.5 | 0 | 0 | 0 |
| 3-3 | 4 | awake | 15 | 76.8 % | 0.2 | 0 | 0 | 0 |
| 4-1 | 4 | awake | 30 | 97.3 % | 0.7 | 0 | 0 | 0 |
| 4-2 | 8 | drowsy | 15 | 69.3 % | 32.2 | 4 | 3 | 0 |
| 4-3 | 9 | drowsy | 15 | 99.6 % | 3.4 | 0 | 0 | 0 |
| 5-1 | 3 | awake | 30 | 98.5 % | 0.0 | 0 | 0 | 0 |
| 5-2 | 7 | drowsy | 15 | 88.6 % | 7.7 | 1 | 1 | 1 |
| 5-3 | 8 | drowsy | 15 | 50.9 % | 8.9 | 0 | 0 | 0 |
| 6-1 | 2 | awake | 30 | 89.5 % | 0.0 | 0 | 0 | 0 |
| 6-2 | 3 | awake | 15 | 53.5 % | 0.0 | 0 | 0 | 0 |
| 6-3 | 7 | drowsy | 15 | 6.1 % | 0.0 | 0 | 0 | 0 |
| 7-2 | 4 | awake | 15 | 99.7 % | 1.2 | 0 | 0 | 0 |
| 7-3 | 9 | drowsy | 15 | 99.1 % | 26.2 | 1 | 1 | 0 |
| 8-1 | 2 | awake | 30 | 99.6 % | 0.1 | 0 | 0 | 0 |
| 8-2 | 6 | between | 15 | 95.2 % | 13.7 | 2 | 1 | 0 |
| 8-3 | 8 | drowsy | 15 | 98.5 % | 15.1 | 2 | 2 | 0 |
| 9-2 | 6 | between | 30 | 97.1 % | 18.6 | 1 | 1 | 0 |
| 9-3 | 8 | drowsy | 30 | 98.9 % | 57.9 | 10 | 10 | 9 |
| 10-1 | 3 | awake | 30 | 73.5 % | 11.0 | 0 | 0 | 0 |
| 10-3 | 7 | drowsy | 30 | 100.0 % | 9.1 | 0 | 0 | 0 |
| 11-1 | 4 | awake | 30 | 100.0 % | 1.2 | 0 | 0 | 0 |
| 11-2 | 7 | drowsy | 30 | 98.8 % | 0.4 | 0 | 0 | 0 |
| 11-3 | 7 | drowsy | 30 | 99.8 % | 0.0 | 0 | 0 | 0 |
| 12-1 | 2 | awake | 30 | 100.0 % | 0.6 | 0 | 0 | 0 |
| 13-1 | 6 | between | 30 | 98.2 % | 8.5 | 0 | 0 | 0 |
| 13-2 | 3 | awake | 30 | 97.6 % | 0.7 | 0 | 0 | 0 |
| 14-1 | 5 | between | 30 | 96.1 % | 0.0 | 0 | 0 | 0 |
| 14-2 | 7 | drowsy | 30 | 100.0 % | 0.8 | 0 | 0 | 0 |
| 14-3 | 8 | drowsy | 30 | 100.0 % | 23.6 | 7 | 7 | 5 |

## What this is not

Not driving data, not the product's colour camera, 14 people, one run. A vote on `l1`, not a measurement of the PRD target. Nothing in `config/thresholds.yaml` was changed by this tool.
