# DriverGuard - evaluation on SUST-DDD (clip labels)

Blocks 5, 7-12 replayed from the traces with config/thresholds.yaml.

2074 clips of ~10 s (975 drowsy, 1099 not drowsy; 163 + 183 min), phone camera in the driver's own car, portrait 720x1280. Full pipeline (blocks 2-12, YOLO on, simulated 60 km/h), fresh state per clip.

Every clip is shorter than `drowsiness.perclos_min_coverage_s` (30 s) and `eye.baseline_min_data_s` (10 s): the PERCLOS term and the driver's own EAR baseline never start. The system can only alert on microsleep (closed_duration), nods, yawns there. The clip-level signals below show what a short window could use.

## 1. System decision per clip

| Rule | Drowsy clips flagged (recall) | Not-drowsy clips flagged (FPR) | Precision | Alerts / hour on not-drowsy clips |
|---|---:|---:|---:|---:|
| any alert L1-L3 | 1.6% | 2.9% | 33.3% | 10.8 |
| L2 or L3 reached | 2.1% | 4.1% | 30.8% |  |
| L3 reached | 1.1% | 0.2% | 84.6% |  |
| any microsleep event | 2.6% | 0.5% | 80.6% |  |
| any yawn event | 0.9% | 0.1% | 90.0% |  |
| any nod event | 1.4% | 1.4% | 48.3% |  |

Alerts by clip class and reason: drowsy: L2 off_road 5, drowsy: L3 microsleep 12, not_drowsy: L2 no_face 7, not_drowsy: L2 off_road 25, not_drowsy: L3 microsleep 2.

## 2. How well each clip-level signal separates drowsy from not-drowsy clips

AUC 0.5 = no information, 1.0 = perfect; oriented so that higher = drowsier (EAR: lower). Medians per class show the direction.

| Signal | AUC | Median drowsy | Median not drowsy | Meaning |
|---|---:|---:|---:|---|
| blink_mean | 0.680 | 0.150 | 0.096 | block 3 MediaPipe eyeBlink, mean |
| perclos_init_base | 0.676 | 0.040 | 0.017 | EAR < 0.65 x baseline_init (what block 7 uses in the first 10 s) |
| closed_frac_block7 | 0.671 | 0.043 | 0.016 | block 7 eye_closed (short-window PERCLOS) |
| ear_p10 | 0.670 | 0.252 | 0.296 | lower = more closed |
| ear_mean | 0.665 | 0.295 | 0.331 | lower = more closed |
| max_closed_duration | 0.659 | 0.080 | 0.033 | block 7 closed_duration |
| blink_closed_frac | 0.639 | 0.017 | 0.004 | eyeBlink ≥ 0.5 (short-window PERCLOS, no baseline needed) |
| blinks_per_min | 0.624 | 18.000 | 12.000 | block 7 blink events / clip length |
| perclos_own_base | 0.622 | 0.064 | 0.033 | EAR < 0.65 x the clip's own p90 EAR |
| reliable_rate | 0.563 | 1.000 | 1.000 | face_conf ≥ min_face_conf |
| face_rate | 0.563 | 1.000 | 1.000 | block 3 |
| cnn_mean | 0.556 | 0.036 | 0.023 | block 5 CNN mean p_closed |
| cnn_closed_frac | 0.540 | 0.003 | 0.000 | block 5 CNN p ≥ 0.6, every frame |
| max_drowsy_score | 0.515 | 0.000 | 0.000 | block 9 drowsy_score |
| microsleep_events | 0.510 | 0.000 | 0.000 | block 7 events |
| yawn_events | 0.504 | 0.000 | 0.000 | block 7 events |
| nod_events | 0.500 | 0.000 | 0.000 | block 7 events |
| any_alert | 0.494 | 0.000 | 0.000 | system decision: any alert L1-L3 |
| max_level | 0.490 | 0.000 | 0.000 | highest risk level in the clip |
| mar_open_frac | 0.485 | 0.000 | 0.000 | MAR ≥ yawn.mar_open |
| pitch_range | 0.467 | 6.520 | 7.056 | p95 - p5 pitch |
| pitch_std | 0.464 | 2.010 | 2.249 | head motion (nodding) |
| off_road_frac | 0.437 | 0.000 | 0.000 | block 8 off_road |
| mar_max | 0.423 | 0.027 | 0.058 | block 6 |

## 3. Face measurability

- Face found on 98.4% of frames; reliable (face_conf ≥ 0.9) on 98.4%.
- Clips with a face on < 50 % of frames: 11; reliable on < 50 %: 11.
