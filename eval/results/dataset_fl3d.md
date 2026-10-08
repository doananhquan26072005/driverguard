# DriverGuard - evaluation on FL3D (frame labels) / NITYMED (videos)

Blocks 5, 7-12 replayed from the traces with config/thresholds.yaml.

Source: commit 9a9c14e (uncommitted changes); thresholds.yaml sha256 6048dd7f4bb4; fl3d_v2.pkl (modified 2026-09-26).

44 NITYMED night-driving videos, 47.2 min at 25 FPS, full pipeline (blocks 2-12, YOLO on, simulated 60 km/h). FL3D labels 53331 of their frames: alert 38954, microsleep 8880, yawning 5497. Frames FL3D left out (outside its crops) are unlabelled and not scored.

Frame alignment check (FL3D `frameN` = video frame N + offset), AUC of MAR for yawning vs alert: -10: 0.962, -5: 0.988, -2: 0.996, +0: 0.997, +2: 0.996, +5: 0.991, +10: 0.973.

## 1. Measurability (blocks 3, 6)

| Label | Frames | Face found | Face reliable (face_conf ≥ min) | Eye state judged (eye_closed not None) | CNN used by pipeline |
|---|---:|---:|---:|---:|---:|
| alert | 38954 | 98.4% | 98.4% | 94.7% | 9.0% |
| microsleep | 8880 | 96.6% | 96.6% | 91.2% | 11.5% |
| yawning | 5497 | 97.2% | 97.2% | 96.6% | 8.6% |

## 2. Per frame: eyes closed (FL3D `microsleep`) vs `alert`

AUC = chance that a microsleep frame scores more closed than an alert frame (0.5 = no signal). Rates over all labelled frames; a frame the system cannot judge counts as not closed.

| Signal | AUC (measured frames) | Rule | Precision | Recall | FPR (alert frames called closed) |
|---|---:|---|---:|---:|---:|
| block 7 eye_closed (hysteresis, EAR or CNN) | 0.936 | eye_closed == 1 | 71.2% | 87.3% | 8.1% |
| EAR / open-eye baseline (block 6/7) | 0.987 | < 0.65 (PERCLOS rule) | 78.6% | 94.0% | 5.8% |
| EAR / baseline, deep | 0.987 | ≤ 0.5 (deep closure) | 89.3% | 88.9% | 2.4% |
| raw EAR | 0.987 | – | – | – | – |
| CNN p_closed, every frame (block 5 diag) | 0.881 | ≥ 0.6 | 81.3% | 29.9% | 1.6% |
| MediaPipe eyeBlink blendshape (block 3) | 0.986 | ≥ 0.5 | 93.4% | 74.2% | 1.2% |

## 3. Per frame: yawning vs alert

| Signal | AUC | Rule | Precision | Recall | FPR |
|---|---:|---|---:|---:|---:|
| MAR (block 6) | 0.997 | ≥ 0.45 | 97.9% | 88.7% | 0.3% |
| block 7 yawning flag | 0.665 | yawning | 97.1% | 33.1% | 0.1% |
| block 7 microsleep mask (yawn / talk) | 0.827 | masked | 29.7% | 98.1% | 32.8% |

## 4. Episodes (runs of one label, gaps ≤ 0.5 s joined)

Detected = the event falls inside the run ± 1 s.

| Labelled microsleep run | Runs | Microsleep event detected |
|---|---:|---:|
| 0–1 s | 118 | 15 (12.7%) |
| 1–1.5 s | 65 | 39 (60.0%) |
| 1.5–3 s | 84 | 73 (86.9%) |
| ≥ 3 s | 11 | 11 (100.0%) |

- Microsleep ≥ 1 s: delay p50 1.00 s after the labelled start.
- Microsleep ≥ 1.5 s (should reach L3 at once): 74/95 got a new L3 alert (77.9%); risk level 3 reached on 77/95 (81.1%) (no new alert: L3 was still active, or its cooldown).
- Yawning runs: 76/99 got a yawn event (76.8%), delay p50 1.56 s.

## 5. Where predictions land

hit = inside a matching labelled run ± 1 s (alerts: any microsleep / yawning run ± 3 s); false = on a frame labelled `alert`, away from every drowsy run; other = another drowsy label or an unlabelled stretch. 26.0 min (0.43 h) of frames are labelled alert: false alarms per hour are over those hours, with an exact Poisson 95 % CI. A few false alarms on 26 minutes say little: no PRD verdict (≤ 1.0 / h) while the CI still spans it.

| Prediction | Total | Hit | False | Other | False / hour of alert frames (95% CI) |
|---|---:|---:|---:|---:|---:|
| microsleep event | 145 | 137 | 4 | 4 | 9.2 (2.52–23.7) |
| yawn event | 76 | 76 | 0 | 0 | 0.0 (0.00–8.5) |
| nod event | 121 | 118 | 1 | 2 | 2.3 (0.06–12.9) |
| perclos_high event | 15 | 5 | 5 | 5 | 11.6 (3.75–27.0) |
| L1 alert | 10 | 9 | 1 | 0 | 2.3 (0.06–12.9) |
| L2 alert | 16 | 13 | 3 | 0 | 6.9 (1.43–20.3) |
| L3 alert | 85 | 83 | 1 | 1 | 2.3 (0.06–12.9) |

Alerts by reason: drowsy_score fp 2, drowsy_score hit 17, microsleep fp 1, microsleep hit 83, microsleep other 1, off_road fp 2, off_road hit 5, repeated_l3 fp 1, repeated_l3 hit 62.

False alerts by reason and level (an alert with two reasons counts under both):

| Reason | Level | False | False / hour (95% CI) |
|---|---:|---:|---:|
| drowsy_score | L1 | 1 | 2.3 (0.06–12.9) |
| drowsy_score | L2 | 1 | 2.3 (0.06–12.9) |
| microsleep | L3 | 1 | 2.3 (0.06–12.9) |
| off_road | L2 | 2 | 4.6 (0.56–16.7) |
| repeated_l3 | L3 | 1 | 2.3 (0.06–12.9) |

## 5b. FAR / MAR on windows (drowsiness)

| Scored | Awake windows | FAR (95% CI) | Drowsy windows | Positive share | MAR (95% CI) | Skipped |
|---|---:|---:|---:|---:|---:|---:|
| Drowsiness, level ≥ L1 | 5 | 60.0% (23.1%–88.2%) | 2 | 2 / 7 (28.6%) | 0.0% (0.0%–65.8%) | 154 |
| Drowsiness, level ≥ L2 | 5 | 20.0% (3.6%–62.4%) | 2 | 2 / 7 (28.6%) | 0.0% (0.0%–65.8%) | 154 |

Unit: one window of 10 s. Positive share: drowsy windows among the scored ones (awake + drowsy).

Windows of 10 s, not overlapping, from 30 s after each clip start (the start-up stretch is left out). Drowsy window: ≥ 50% inside a labelled episode; awake window: ≥ 50% known-awake and not touching an episode; others skipped. Predicted: the branch's risk level reaches the stated level in the window. Wilson CI; windows of one clip are correlated, so the CI is optimistic.

Drowsy = FL3D microsleep / yawning frames; awake = frames labelled alert; frames FL3D left out are unlabelled. Distraction is not labelled in FL3D.

Read with care: the videos are ~1 min (30 s start-up left out) and dense with microsleep / yawning runs, so few windows qualify. FL3D `alert` frames sit between the microsleeps of the same drowsy actor, and `drowsy_score` is meant to stay up for minutes after a microsleep: a high FAR here is not an awake driver disturbed. FAR / MAR are for long recordings (UTA-RLDD, DMD).

## 6. Per video

| Video | Min | Face | Microsleep runs ≥1 s (detected) | Yawn runs (detected) | Alerts L1/L2/L3 | False alerts |
|---|---:|---:|---:|---:|---:|---:|
| P1042751 | 2.1 | 98.9% | 4 (0) | 0 (0) | 1/2/0 | 0 |
| P1042756 | 2.1 | 93.8% | 7 (0) | 2 (0) | 0/3/0 | 2 |
| P1042757 | 2.4 | 99.7% | 4 (0) | 0 (0) | 0/1/0 | 0 |
| P1042762 | 2.1 | 100.0% | 14 (9) | 1 (1) | 1/2/4 | 0 |
| P1042767 | 2.2 | 96.8% | 9 (9) | 5 (0) | 1/1/7 | 0 |
| P1042772 | 2.1 | 93.7% | 14 (10) | 0 (0) | 0/1/8 | 0 |
| P1042777 | 2.1 | 93.1% | 11 (11) | 0 (0) | 0/1/10 | 0 |
| P1042780 | 0.7 | 96.8% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1042787 | 2.2 | 99.1% | 1 (1) | 1 (1) | 1/0/0 | 0 |
| P1042793 | 2.1 | 97.5% | 14 (13) | 0 (0) | 0/1/10 | 2 |
| P1042797 | 2.1 | 98.3% | 18 (14) | 0 (0) | 1/0/10 | 0 |
| P1043066 | 0.5 | 88.5% | 0 (0) | 5 (3) | 0/0/0 | 0 |
| P1043067 | 2.2 | 99.8% | 12 (12) | 0 (0) | 0/0/10 | 0 |
| P1043068 | 2.4 | 98.8% | 16 (11) | 0 (0) | 1/2/4 | 0 |
| P1043075 | 2.2 | 98.3% | 13 (12) | 0 (0) | 1/1/10 | 0 |
| P1043076 | 0.5 | 99.1% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043078 | 0.4 | 97.4% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043079 | 0.4 | 97.8% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043080 | 0.4 | 92.9% | 0 (0) | 4 (3) | 0/0/0 | 0 |
| P1043081 | 0.4 | 97.8% | 0 (0) | 4 (3) | 0/0/0 | 0 |
| P1043086 | 0.4 | 99.8% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043087 | 0.4 | 100.0% | 0 (0) | 3 (2) | 0/0/0 | 0 |
| P1043089 | 2.1 | 98.5% | 16 (16) | 0 (0) | 0/0/10 | 0 |
| P1043106 | 2.1 | 99.0% | 0 (0) | 0 (0) | 1/0/1 | 1 |
| P1043115 | 2.0 | 99.8% | 3 (3) | 0 (0) | 1/1/1 | 0 |
| P1043116 | 0.3 | 98.9% | 0 (0) | 3 (2) | 0/0/0 | 0 |
| P1043117 | 0.3 | 100.0% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043118 | 0.4 | 100.0% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043119 | 0.3 | 100.0% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043120 | 0.3 | 100.0% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043121 | 0.4 | 100.0% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043122 | 2.1 | 100.0% | 4 (2) | 0 (0) | 1/0/0 | 0 |
| P1043123 | 0.4 | 98.9% | 0 (0) | 3 (2) | 0/0/0 | 0 |
| P1043124 | 0.4 | 100.0% | 0 (0) | 3 (2) | 0/0/0 | 0 |
| P1043125 | 0.3 | 100.0% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043126 | 0.4 | 100.0% | 0 (0) | 3 (2) | 0/0/0 | 0 |
| P1043127 | 0.3 | 100.0% | 0 (0) | 3 (2) | 0/0/0 | 0 |
| P1043128 | 0.3 | 100.0% | 0 (0) | 3 (2) | 0/0/0 | 0 |
| P1043130 | 0.2 | 98.4% | 0 (0) | 4 (3) | 0/0/0 | 0 |
| P1043131 | 0.4 | 98.2% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043132 | 0.5 | 99.6% | 0 (0) | 5 (3) | 0/0/0 | 0 |
| P1043133 | 0.5 | 100.0% | 0 (0) | 3 (3) | 0/0/0 | 0 |
| P1043134 | 0.4 | 100.0% | 0 (0) | 4 (3) | 0/0/0 | 0 |
| P1043135 | 0.5 | 100.0% | 0 (0) | 4 (3) | 0/0/0 | 0 |

False alerts (video, time, level, reasons): P1043106 31.0s L1 drowsy_score; P1042793 86.4s L2 drowsy_score; P1042793 122.8s L3 microsleep,repeated_l3; P1042756 11.4s L2 off_road; P1042756 58.6s L2 off_road.
