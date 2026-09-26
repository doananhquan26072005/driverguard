# DriverGuard - evaluation on FL3D (frame labels) / NITYMED (videos)

Blocks 5, 7-12 replayed from the traces with config/thresholds.yaml.

44 NITYMED night-driving videos, 47.2 min at 25 FPS, full pipeline (blocks 2-12, YOLO on, simulated 60 km/h). FL3D labels 53331 of their frames: alert 38954, microsleep 8880, yawning 5497. Frames FL3D left out (outside its crops) are unlabelled and not scored.

Frame alignment check (FL3D `frameN` = video frame N + offset), AUC of MAR for yawning vs alert: -10: 0.962, -5: 0.988, -2: 0.996, +0: 0.997, +2: 0.996, +5: 0.991, +10: 0.973.

## 1. Measurability (blocks 3, 6)

| Label | Frames | Face found | Face reliable (face_conf ≥ min) | Eye state judged (eye_closed not None) | CNN used by pipeline |
|---|---:|---:|---:|---:|---:|
| alert | 38954 | 98.4% | 98.4% | 94.7% | 9.0% |
| microsleep | 8880 | 96.6% | 96.6% | 91.4% | 11.5% |
| yawning | 5497 | 97.2% | 97.2% | 96.6% | 8.6% |

## 2. Per frame: eyes closed (FL3D `microsleep`) vs `alert`

AUC = chance that a microsleep frame scores more closed than an alert frame (0.5 = no signal). Rates over all labelled frames; a frame the system cannot judge counts as not closed.

| Signal | AUC (measured frames) | Rule | Precision | Recall | FPR (alert frames called closed) |
|---|---:|---|---:|---:|---:|
| block 7 eye_closed (hysteresis, EAR or CNN) | 0.935 | eye_closed == 1 | 72.1% | 87.0% | 7.7% |
| EAR / open-eye baseline (block 6/7) | 0.987 | < 0.65 (PERCLOS rule) | 78.5% | 94.0% | 5.9% |
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
- Microsleep ≥ 1.5 s (should reach L3 at once): 72/95 got a new L3 alert (75.8%); risk level 3 reached on 75/95 (78.9%) (the gap is the L3 cooldown).
- Yawning runs: 76/99 got a yawn event (76.8%), delay p50 1.56 s.

## 5. Where predictions land

hit = inside a matching labelled run ± 1 s (alerts: any microsleep / yawning run ± 3 s); false = on a frame labelled `alert`, away from every drowsy run; other = another drowsy label or an unlabelled stretch. 26.0 min of frames are labelled alert.

| Prediction | Total | Hit | False | Other | False / hour of alert frames |
|---|---:|---:|---:|---:|---:|
| microsleep event | 146 | 137 | 4 | 5 | 9.2 |
| yawn event | 76 | 76 | 0 | 0 | 0.0 |
| nod event | 118 | 115 | 1 | 2 | 2.3 |
| perclos_high event | 15 | 5 | 5 | 5 | 11.6 |
| L1 alert | 10 | 9 | 1 | 0 | 2.3 |
| L2 alert | 13 | 9 | 3 | 1 | 6.9 |
| L3 alert | 83 | 81 | 1 | 1 | 2.3 |

Alerts by reason: drowsy_score fp 2, drowsy_score hit 16, drowsy_score other 1, microsleep fp 1, microsleep hit 81, microsleep other 1, off_road fp 2, off_road hit 2.

## 6. Per video

| Video | Min | Face | Microsleep runs ≥1 s (detected) | Yawn runs (detected) | Alerts L1/L2/L3 | False alerts |
|---|---:|---:|---:|---:|---:|---:|
| P1042751 | 2.1 | 98.9% | 4 (0) | 0 (0) | 1/1/0 | 0 |
| P1042756 | 2.1 | 93.8% | 7 (0) | 2 (0) | 0/3/0 | 2 |
| P1042757 | 2.4 | 99.7% | 4 (0) | 0 (0) | 0/0/0 | 0 |
| P1042762 | 2.1 | 100.0% | 14 (9) | 1 (1) | 1/1/3 | 0 |
| P1042767 | 2.2 | 96.8% | 9 (9) | 5 (0) | 1/1/7 | 0 |
| P1042772 | 2.1 | 93.7% | 14 (10) | 0 (0) | 0/1/8 | 0 |
| P1042777 | 2.1 | 93.1% | 11 (11) | 0 (0) | 0/1/9 | 0 |
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

False alerts (video, time, level, reasons): P1042793 86.4s L2 drowsy_score; P1042793 122.8s L3 microsleep; P1043106 31.0s L1 drowsy_score; P1042756 11.4s L2 off_road; P1042756 58.6s L2 off_road.
