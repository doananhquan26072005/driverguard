# DriverGuard - PERCLOS: the current definition against P80

Blocks 7-12 replayed on the stored traces (`tools/trace_studies.py perclos`). No threshold was changed.

- **Current** `perclos_60s`: a frame is closed when EAR < 0.65 x the open-eye baseline (an opening below ~46 %, close to "P50"); frames block 5 decided count on p_closed ≥ 0.6; frames masked for yawning / talking are skipped.
- **P80** (the definition PERCLOS has in the literature): opening below 20 %, i.e. EAR < 0.48 x baseline without enrollment (closed EAR taken as 0.35 x baseline). EAR frames only: a CNN probability is not an opening.

## 1. Share of frames closed under each definition

Whole-clip fraction (the clips are shorter than, or about as long as, the 60 s window). Median and p90 over the clips; last column: clips whose fraction is at or above `perclos_drowsy` (0.15).

| Dataset | Clips | Definition | Median | p90 | Clips ≥ threshold |
|---|---|---|---:|---:|---:|
| fl3d | all (44) | current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on) | 12.8% | 31.4% | 21 (47.7%) |
| fl3d | all (44) | same EAR test, EAR frames only, no mask | 20.3% | 35.0% | 28 (63.6%) |
| fl3d | all (44) | P80: opening < 20 %, EAR frames only | 12.0% | 27.9% | 16 (36.4%) |
| fl3d | all (44) | P80 without closures shorter than a blink | 5.1% | 21.0% | 10 (22.7%) |
| yawdd | normal / talking (205) | current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on) | 4.9% | 17.3% | 28 (13.7%) |
| yawdd | normal / talking (201) | same EAR test, EAR frames only, no mask | 6.7% | 21.9% | 39 (19.4%) |
| yawdd | normal / talking (201) | P80: opening < 20 %, EAR frames only | 3.5% | 12.3% | 12 (6.0%) |
| yawdd | normal / talking (201) | P80 without closures shorter than a blink | 0.0% | 2.6% | 0 (0.0%) |
| yawdd | yawning (114) | current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on) | 4.1% | 13.4% | 8 (7.0%) |
| yawdd | yawning (112) | same EAR test, EAR frames only, no mask | 6.7% | 25.0% | 31 (27.7%) |
| yawdd | yawning (112) | P80: opening < 20 %, EAR frames only | 4.3% | 21.3% | 21 (18.8%) |
| yawdd | yawning (112) | P80 without closures shorter than a blink | 0.0% | 10.8% | 5 (4.5%) |
| sust | not drowsy (1094) | current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on) | 1.2% | 7.8% | 39 (3.6%) |
| sust | not drowsy (1085) | same EAR test, EAR frames only, no mask | 1.3% | 8.4% | 34 (3.1%) |
| sust | not drowsy (1085) | P80: opening < 20 %, EAR frames only | 0.8% | 5.9% | 24 (2.2%) |
| sust | not drowsy (1085) | P80 without closures shorter than a blink | 0.0% | 0.0% | 7 (0.6%) |
| sust | drowsy (975) | current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on) | 3.6% | 14.3% | 90 (9.2%) |
| sust | drowsy (970) | same EAR test, EAR frames only, no mask | 3.7% | 14.7% | 94 (9.7%) |
| sust | drowsy (970) | P80: opening < 20 %, EAR frames only | 2.4% | 11.4% | 59 (6.1%) |
| sust | drowsy (970) | P80 without closures shorter than a blink | 0.0% | 5.4% | 21 (2.2%) |

Frames block 5 decided (not judged by P80), share of the judged frames: fl3d 5.8% on average, 22.8% in the worst clip; yawdd 25.7% on average, 100.0% in the worst clip; sust 7.3% on average, 100.0% in the worst clip.

## 2. Does either definition separate drowsy from alert better?

SUST, per clip (975 drowsy, 1099 not drowsy): AUC of the clip's closed fraction (0.5 = no information).

| Definition | AUC | Median drowsy | Median not drowsy |
|---|---:|---:|---:|
| current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on) | 0.669 | 3.6% | 1.2% |
| same EAR test, EAR frames only, no mask | 0.664 | 3.7% | 1.3% |
| P80: opening < 20 %, EAR frames only | 0.649 | 2.4% | 0.8% |
| P80 without closures shorter than a blink | 0.538 | 0.0% | 0.0% |

FL3D, per labelled frame (8880 `microsleep`, 38954 `alert`): a frame the definition cannot judge counts as not closed.

| Definition | Microsleep frames closed (recall) | Alert frames closed (FPR) | Precision | Frames it can judge |
|---|---:|---:|---:|---:|
| current `perclos_60s` (EAR < 0.65 x baseline, or CNN; mask on) | 70.5% | 2.6% | 85.9% | 66.5% |
| same EAR test, EAR frames only, no mask | 81.4% | 5.1% | 78.6% | 86.9% |
| P80: opening < 20 %, EAR frames only | 77.3% | 2.0% | 90.0% | 86.9% |
| P80 without closures shorter than a blink | 66.5% | 0.9% | 94.6% | 86.9% |

## 3. The 60 s window as the agent computes it

`perclos_60s` (current) and `perclos_p80_60s` (measured next to it since M40) on the frames where the current one is ready (`perclos_min_coverage_s` of eye data). Only clips long enough get there.

| Dataset | Frames with a ready window | Current: median / p90 | P80: median / p90 | P80 eye-data seconds, median |
|---|---:|---:|---:|---:|
| fl3d | 30325 | 24.0% / 36.5% | 20.9% / 34.4% | 51 |
| yawdd | 0 | – | – | – |
| sust | 0 | – | – | – |

## 4. What-if: the PERCLOS rule on the P80-equivalent threshold (`perclos_close_ratio` = 0.48)

Same thresholds otherwise (`perclos_drowsy`, `risk.drowsy.perclos_low / perclos_high` untouched), so this shows the direction, not a tuned result. CNN frames still count by probability here. Alerts per hour with an exact Poisson 95 % CI, on the clips where an alert is a false alarm (SUST not drowsy, YawDD normal / talking); FL3D has no such clips, all its alerts are listed.

| Dataset | Clips | Hours | Setting | `perclos_high` events | `drowsy_score` alerts | All alerts | All alerts / hour (95% CI) |
|---|---|---:|---|---:|---:|---:|---:|
| fl3d | all (44) | 0.79 | current (0.65) | 15 | 21 | 111 | 141.2 (116.14–170.0) |
| fl3d | all (44) | 0.79 | P80-equivalent (0.48) | 15 | 22 | 112 | 142.5 (117.30–171.4) |
| yawdd | no drowsiness (205) | 1.45 | current (0.65) | 0 | 0 | 10 | 6.9 (3.31–12.7) |
| yawdd | no drowsiness (205) | 1.45 | P80-equivalent (0.48) | 0 | 0 | 10 | 6.9 (3.31–12.7) |
| sust | no drowsiness (1099) | 3.05 | current (0.65) | 0 | 0 | 27 | 8.8 (5.83–12.9) |
| sust | no drowsiness (1099) | 3.05 | P80-equivalent (0.48) | 0 | 0 | 27 | 8.8 (5.83–12.9) |
| sust | drowsy (975) | 2.71 | current (0.65) | 0 | 0 | clips with an alert: 16 (1.6%) | – |
| sust | drowsy (975) | 2.71 | P80-equivalent (0.48) | 0 | 0 | clips with an alert: 16 (1.6%) | – |

## Reading it

- These clips are short (SUST 10 s, YawDD ~20 s, FL3D ~30 s): the 60 s PERCLOS window rarely fills, so the PERCLOS rule seldom fires under either definition. A verdict on which definition detects drowsiness better needs long recordings of the same person awake and drowsy (UTA-RLDD).
- If the thresholds are ever moved to P80, `perclos_drowsy` and `risk.drowsy.perclos_low / perclos_high` have to be tuned again on that data: they were set with the current definition.
- Source: Abe T. PERCLOS-based technologies for detecting drowsiness: current evidence and future directions. SLEEP Advances 2023;4(1):zpad006. https://doi.org/10.1093/sleepadvances/zpad006
