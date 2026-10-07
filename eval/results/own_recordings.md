# DriverGuard - own recordings (numbers from the camera, key-press labels)

12 recordings, 72.0 min. Full pipeline (blocks 2-12) on the camera frames at a simulated constant speed; one row of numbers per frame, no image stored. Labels are key presses of the person acting, matched ± 1 s (`eval.label_tolerance_s`). Acted by the team: a development set, not evidence for real driving.

## 1. Recordings

| Recording | Tags | Min | FPS | Face found | Face reliable | Labels | Alerts L1/L2/L3 |
|---|---|---:|---:|---:|---:|---:|---:|
| dark | glasses=no, light=dark, person=quan | 1.9 | 29.6 | 100% | 100% | 12 | 0/0/0 |
| dark_35 | glasses=no, light=dim, person=quan | 3.0 | 29.8 | 100% | 100% | 18 | 0/0/17 |
| dark_35_still | glasses=no, light=dim, person=quan | 5.5 | 29.9 | 100% | 100% | 1 | 2/0/8 |
| dark_low | glasses=no, light=dim, person=quan | 2.9 | 29.7 | 100% | 100% | 11 | 0/0/0 |
| dark_mid | glasses=no, light=dim, person=quan | 2.4 | 29.7 | 100% | 100% | 11 | 0/0/10 |
| day_eyes | glasses=no, light=day, person=quan | 5.1 | 29.8 | 99% | 99% | 30 | 1/1/13 |
| day_look | glasses=no, light=day, person=quan | 8.2 | 29.9 | 97% | 97% | 12 | 2/6/3 |
| day_phone | glasses=no, light=day, person=quan | 6.9 | 29.9 | 99% | 99% | 10 | 1/9/1 |
| glances | glasses=no, light=day, person=quan | 6.7 | 29.9 | 100% | 100% | 16 | 0/0/0 |
| head_turn | glasses=no, light=day, person=quan | 8.0 | 29.9 | 99% | 99% | 10 | 0/6/0 |
| look_down | glasses=no, light=day, person=quan | 13.4 | 29.9 | 100% | 100% | 28 | 1/1/9 |
| phone_holds | glasses=no, light=day, person=quan | 8.2 | 29.9 | 100% | 100% | 10 | 1/9/2 |

## 2. Time to alert (PRD: p95 ≤ 3 s)

Delay = first matching alert (or block 7 event) minus the key press. Eyes closed: only spells of at least `risk.microsleep_l3_s` (1.5 s) are expected to reach L3; shorter ones are listed apart.

| Action | Expected | Labelled | Answered | Delay p50 (s) | Delay p95 (s) | Slowest (s) |
|---|---|---:|---:|---:|---:|---:|
| eyes_closed ≥ 1.5 s | alert microsleep | 59 | 38 (64%) | 1.87 | 2.03 | 2.07 |
| eyes_closed < 1.5 s | alert microsleep | 3 | 2 (67%) | 1.58 | 1.63 | 1.63 |
| look_down_phone | alert off_road | 7 | 0 (0%) | – | – | – |
| look_dashboard | alert off_road | 6 | 0 (0%) | – | – | – |
| look_side | alert off_road | 8 | 8 (100%) | 2.98 | 3.04 | 3.04 |
| look_behind | alert off_road | 2 | 2 (100%) | 2.83 | 2.83 | 2.83 |
| phone_call | alert phone | 9 | 9 (100%) | 2.40 | 2.75 | 2.77 |
| phone_text | alert phone | 11 | 6 (55%) | 3.15 | 4.71 | 4.83 |
| yawn | event yawn | 5 | 5 (100%) | 1.97 | 2.04 | 2.04 |
| nod | event nod | 18 | 11 (61%) | 1.77 | 2.32 | 2.50 |
| look_mount | alert off_road | 3 | 0 (0%) | – | – | – |
| look_gear | alert off_road | 3 | 0 (0%) | – | – | – |
| glance_repeat | alert off_road | 4 | 0 (0%) | – | – | – |
| bow_eyes_closed | alert microsleep | 7 | 7 (100%) | 1.90 | 1.99 | 2.00 |
| look_partial | alert off_road | 5 | 1 (20%) | 3.16 | 3.16 | 3.16 |

## 3. Alerts that answer no label

- 29 alerts outside every labelled action that expects one, on 0.94 h: 30.9 (20.72–44.4) per hour (exact Poisson 95 % CI). Unlabelled time is taken as normal driving posture; an action the person forgot to label counts against the system here.
- 10 alerts inside `talking` / `awake_still` / `mirror_check` (9.3 min): 64.4 (30.90–118.5) per hour.
- By reason and level: drowsy_score L1 7, drowsy_score L2 5, microsleep L3 16, repeated_l1 L2 1, repeated_l3 L3 6, trend L1 3, trend L2 1, unresponsive L3 2.

## 4. Looking down or eyes closed (numbers per kind of action)

p10 / p50 / p90 over the frames of the labelled intervals. EAR ratio = EAR / the open-eye baseline of that moment; pitch in degrees (> 0 = head down); eyeBlink, eyeLookDown: MediaPipe blendshapes (mean of both eyes).

| Action | Frames | EAR ratio | eyeBlink | eyeLookDown | Pitch | Iris y | Block 7 closed | Masked |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| awake_still | 14617 | 0.69 / 0.89 / 1.00 | 0.03 / 0.08 / 0.20 | 0.06 / 0.15 / 0.35 | -6.04 / -3.54 / 5.03 | -0.08 / -0.07 / -0.05 | 20% | 40% |
| eyes_closed | 6063 | 0.05 / 0.12 / 0.88 | 0.10 / 0.64 / 0.70 | 0.17 / 0.71 / 0.78 | -11.94 / -3.87 / 5.46 | -0.07 / 0.01 / 0.03 | 81% | 47% |
| bow_eyes_closed | 841 | 0.11 / 0.15 / 0.90 | 0.07 / 0.67 / 0.72 | 0.15 / 0.63 / 0.70 | -4.62 / 10.10 / 14.59 | -0.08 / 0.05 / 0.06 | 80% | 8% |
| look_down_phone | 1185 | 0.21 / 0.34 / 0.89 | 0.08 / 0.48 / 0.57 | 0.16 / 0.57 / 0.63 | -4.11 / 3.81 / 6.02 | -0.07 / 0.03 / 0.05 | 76% | 0% |
| look_mount | 543 | 0.53 / 0.62 / 0.80 | 0.12 / 0.26 / 0.33 | 0.37 / 0.63 / 0.67 | -9.73 / -7.59 / -5.82 | -0.06 / 0.00 / 0.01 | 55% | 0% |
| look_dashboard | 1042 | 0.61 / 0.81 / 0.96 | 0.05 / 0.13 / 0.24 | 0.19 / 0.44 / 0.55 | -13.07 / -9.11 / -3.07 | -0.08 / -0.05 / -0.01 | 18% | 0% |
| look_gear | 505 | 0.53 / 0.66 / 0.99 | 0.05 / 0.27 / 0.39 | 0.21 / 0.52 / 0.62 | -9.50 / -6.86 / -4.61 | -0.08 / -0.02 / -0.00 | 35% | 0% |
| look_partial | 646 | 0.73 / 0.85 / 0.94 | 0.08 / 0.15 / 0.25 | 0.30 / 0.46 / 0.56 | -9.69 / -7.35 / -4.55 | -0.06 / -0.04 / -0.02 | 3% | 55% |
| look_side | 1317 | 0.81 / 1.82 / 2.74 | 0.04 / 0.10 / 0.28 | 0.07 / 0.21 / 0.53 | -45.38 / -9.94 / -4.68 | -0.32 / -0.11 / 0.10 | 3% | 83% |
| glance_repeat | 3822 | 0.73 / 1.02 / 1.64 | 0.03 / 0.07 / 0.26 | 0.05 / 0.19 / 0.50 | -17.21 / -12.53 / -5.69 | -0.22 / -0.13 / -0.06 | 7% | 34% |
| mirror_check | 1020 | 0.78 / 0.96 / 1.06 | 0.02 / 0.04 / 0.11 | 0.02 / 0.07 / 0.31 | -28.77 / -17.37 / -7.82 | -0.20 / -0.16 / -0.09 | 6% | 0% |
| talking | 1020 | 0.68 / 0.87 / 1.02 | 0.04 / 0.10 / 0.21 | 0.04 / 0.25 / 0.45 | -12.70 / -9.49 / -6.67 | -0.12 / -0.06 / -0.03 | 14% | 99% |
| yawn | 622 | 0.16 / 0.34 / 0.74 | 0.19 / 0.38 / 0.52 | 0.19 / 0.39 / 0.57 | -11.35 / -8.37 / -5.60 | -0.06 / -0.04 / -0.01 | 88% | 88% |

## 5. By `mask` tag (mouth covered or not)

MAR reversals: direction changes of at least `microsleep_mask.talk_swing` (0.08) per minute of `awake_still` (a still mouth should have none; many would switch the talking mask on and hide closed eyes). L3 reached: labelled closed-eye spells of at least 1.5 s during which the risk level got to 3.

| mask | Min | Face found | MAR still (p10 / p50 / p90) | MAR reversals / min still | Masked while still | Yawns labelled | Yawn events in them | Yawn events elsewhere | Closed spells | L3 reached | Masked during them |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| not tagged | 72.0 | 99% | 0.01 / 0.02 / 0.18 | 53.8 | 40% | 5 | 5 | 2 | 59 | 38 (64%) | 48% |

## 6. Call or text (block 4 `phone_kind` against the label)

| Labelled | Frames | Phone in the driver zone | Recorded call | Recorded text | Recorded unknown |
|---|---:|---:|---:|---:|---:|
| call | 1930 | 86% | 1725 | 0 | 0 |
| text | 2562 | 53% | 0 | 1867 | 0 |
