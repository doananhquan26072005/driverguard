# DriverGuard - UTA-RLDD, the same videos at a lower frame rate (dev)

Thresholds: config/thresholds.yaml; block 5 decided again from the traced inputs. Source: commit 9a9c14e (uncommitted changes); thresholds.yaml sha256 e989dce82c7e; index.csv (modified 2026-10-06).

59 videos of 21 subjects, all recorded at 25 FPS or more, replayed through blocks 7-12 with frames left out: the loop asks for a frame every 1 / rate seconds and gets the first recorded frame at or after that moment, with the time it was taken. Nothing but the frames a slow device would not have processed is removed. "uneven": the waits are log-normal around 1 / rate (coefficient of variation 0.3). 3 runs per row: the even runs start their grid at another moment, the uneven ones draw other waits. A cell with one number: every run agrees; otherwise mean (lowest–highest). The spread between runs of one row is noise: a difference between two rows smaller than that is not a finding.

Not covered: blocks 2-5 on a slow device (the landmarks here were computed on every frame of a fast machine; only the decision blocks see fewer of them), the phone branch (no detector in these traces), frame quality gating, enrollment. Measured only: no threshold was changed.

## 1. Alerts

False alarms: alerts on `0` (awake) videos. "Drowsiness" = drowsiness-branch alerts after the 30 s start-up stretch, per scored hour. "Every branch" = every alert of the whole video, per hour of video (what the PRD counts). A gap above 500 ms (`max_gap_s`) is not a slow frame for blocks 7, 8 and 12 but a hole: running timers start again (M71).

| Loop | Frames / s | Gap p50 / p95 / max (ms) | Drowsiness false alarms | / h | Every branch | / h | `0` subjects with one | `10` subjects alerted | reaching L3 | `5` alerted | AUC of the mean score |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| as recorded | 30.0 | 33 / 33 / 40 | 5 | 1.55 | 10 | 2.95 | 2 / 20 | 12 / 19 | 10 | 5 / 20 | 0.892 |
| 15 FPS, even | 15.0 | 67 / 67 / 100 | 5.7 (4–7) | 1.76 (1.24–2.17) | 10.7 (9–12) | 3.15 (2.65–3.54) | 2.7 (2–3) / 20 | 12.7 (12–14) / 19 | 10 | 5.0 (4–6) / 20 | 0.879 (0.874–0.887) |
| 15 FPS, uneven | 15.0 | 67 / 100 / 333 | 3.7 (3–4) | 1.14 (0.93–1.24) | 8.0 (7–9) | 2.36 (2.06–2.65) | 1.7 (1–2) / 20 | 13 / 19 | 10.3 (10–11) | 4.0 (3–5) / 20 | 0.886 (0.876–0.895) |
| 12 FPS, even | 12.0 | 67 / 100 / 120 | 4.0 (3–5) | 1.24 (0.93–1.55) | 8.7 (7–10) | 2.56 (2.06–2.95) | 1.7 (1–2) / 20 | 12.7 (12–13) / 19 | 10.3 (10–11) | 4.7 (4–5) / 20 | 0.886 (0.878–0.889) |
| 12 FPS, uneven | 12.0 | 67 / 133 / 433 | 4.0 (3–5) | 1.24 (0.93–1.55) | 8.3 (7–10) | 2.46 (2.06–2.95) | 2.0 (1–3) / 20 | 12.3 (12–13) / 19 | 9.3 (9–10) | 4.7 (4–5) / 20 | 0.886 (0.875–0.892) |
| 10 FPS, even | 10.0 | 100 / 100 / 133 | 3.7 (2–6) | 1.14 (0.62–1.86) | 8.0 (6–10) | 2.36 (1.77–2.95) | 2.0 (1–3) / 20 | 12.7 (12–13) / 19 | 10.3 (10–11) | 5.0 (4–6) / 20 | 0.881 (0.864–0.897) |
| 10 FPS, uneven | 10.0 | 100 / 167 / 533 | 3.3 (3–4) | 1.03 (0.93–1.24) | 8.0 (7–9) | 2.36 (2.06–2.65) | 1.3 (1–2) / 20 | 12.7 (12–13) / 19 | 9.7 (9–10) | 4.3 (4–5) / 20 | 0.887 (0.882–0.892) |

As recorded: 3.22 h of awake video scored (3.39 h whole), 20 / 19 / 20 subjects with a `0` / `10` / `5` video.

## 2. What block 7 measures

Events per scored hour and means over the videos of a label (start-up stretch left out). A signal that follows the frame rate, with nothing else changed, is measured by frames, not by time.

`0` videos:

| Loop | Blinks / min | Microsleep events / h | Yawns / h | Nods / h | PERCLOS-high events / h | Mean PERCLOS | Mean drowsy_score | Longest closure (s), median | Blink duration (s), median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| as recorded | 12.4 | 0.3 | 0.0 | 2.5 | 1.6 | 0.033 | 3.8 | 0.32 | 0.301 |
| 15 FPS, even | 11.8 (11.8–11.8) | 0.5 (0.3–0.6) | 0.0 | 2.3 (1.9–2.5) | 1.8 (1.6–1.9) | 0.033 (0.033–0.033) | 4.1 (3.6–4.4) | 0.29 (0.23–0.33) | 0.323 (0.321–0.326) |
| 15 FPS, uneven | 11.5 (11.4–11.6) | 0.3 | 0.0 | 2.1 (1.9–2.5) | 1.7 (1.6–1.9) | 0.033 (0.033–0.033) | 3.7 (3.6–3.8) | 0.27 (0.25–0.30) | 0.331 (0.327–0.334) |
| 12 FPS, even | 11.2 (11.1–11.4) | 0.3 | 0.0 | 2.0 (1.9–2.2) | 1.6 (1.2–1.9) | 0.033 (0.033–0.033) | 3.7 (3.6–3.8) | 0.26 (0.25–0.27) | 0.335 (0.331–0.337) |
| 12 FPS, uneven | 11.0 (10.9–11.0) | 0.3 | 0.0 | 1.9 (1.6–2.2) | 1.7 (1.6–1.9) | 0.033 (0.033–0.033) | 3.7 (3.6–3.7) | 0.28 (0.27–0.30) | 0.341 (0.339–0.343) |
| 10 FPS, even | 10.9 (10.9–10.9) | 0.3 | 0.0 | 2.2 (1.6–2.8) | 1.4 (1.2–1.6) | 0.033 (0.033–0.033) | 3.5 (3.0–4.0) | 0.28 (0.25–0.30) | 0.347 (0.345–0.351) |
| 10 FPS, uneven | 10.4 (10.3–10.5) | 0.3 | 0.0 | 2.1 (1.6–2.8) | 1.6 (1.2–1.9) | 0.033 (0.033–0.033) | 3.7 (3.7–3.8) | 0.28 (0.27–0.28) | 0.356 (0.355–0.358) |

`10` videos:

| Loop | Blinks / min | Microsleep events / h | Yawns / h | Nods / h | PERCLOS-high events / h | Mean PERCLOS | Mean drowsy_score | Longest closure (s), median | Blink duration (s), median |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| as recorded | 16.3 | 25.7 | 2.3 | 0.3 | 5.9 | 0.105 | 22.9 | 1.84 | 0.355 |
| 15 FPS, even | 15.6 (15.6–15.6) | 26.3 (25.7–27.0) | 2.3 | 0.5 (0.3–0.7) | 6.1 (5.9–6.5) | 0.105 (0.104–0.105) | 23.8 (23.4–24.1) | 1.74 (1.67–1.87) | 0.377 (0.372–0.385) |
| 15 FPS, uneven | 15.3 (15.3–15.3) | 24.5 (24.1–25.0) | 2.3 | 0.2 (0.0–0.3) | 6.1 (5.9–6.2) | 0.105 (0.104–0.105) | 22.5 (22.1–22.7) | 1.81 (1.74–1.87) | 0.382 (0.377–0.390) |
| 12 FPS, even | 15.0 (14.9–15.0) | 25.7 (25.4–26.0) | 2.4 (2.0–2.6) | 0.4 (0.0–1.0) | 6.1 (5.5–6.5) | 0.105 (0.104–0.105) | 23.4 (23.1–23.9) | 1.67 (1.57–1.84) | 0.396 (0.385–0.404) |
| 12 FPS, uneven | 14.7 (14.6–14.8) | 26.2 (25.4–27.0) | 2.2 (2.0–2.3) | 0.3 | 6.3 (6.2–6.5) | 0.105 (0.104–0.105) | 23.3 (23.0–23.6) | 1.41 (1.17–1.60) | 0.394 (0.392–0.398) |
| 10 FPS, even | 14.6 (14.5–14.7) | 25.5 (24.1–26.7) | 2.3 (2.0–2.6) | 0.8 (0.7–1.0) | 6.2 (5.9–6.5) | 0.105 (0.104–0.105) | 22.9 (21.9–23.8) | 1.80 (1.80–1.80) | 0.399 (0.395–0.401) |
| 10 FPS, uneven | 14.1 (14.1–14.1) | 25.9 (25.4–26.3) | 2.4 (2.3–2.6) | 0.2 (0.0–0.3) | 6.2 | 0.104 (0.104–0.105) | 23.3 (23.0–23.8) | 1.52 (1.17–1.80) | 0.410 (0.408–0.412) |

## 3. Videos whose drowsiness alerts change

20 of 59 videos have another number of drowsiness-branch alerts (whole video) in at least one run. One number per run.

| Video | Label | As recorded | 15 FPS, even | 15 FPS, uneven | 12 FPS, even | 12 FPS, uneven | 10 FPS, even | 10 FPS, uneven |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| F1_S01_0 | 0 | 2 | 1 / 1 / 2 | 1 / 1 / 0 | 1 / 0 / 2 | 1 / 1 / 0 | 2 / 1 / 0 | 0 / 1 / 0 |
| F2_S15_0 | 0 | 4 | 4 / 4 / 4 | 4 / 4 / 4 | 4 / 4 / 4 | 4 / 4 / 4 | 4 / 1 / 4 | 4 / 4 / 4 |
| F2_S20_0 | 0 | 0 | 2 / 0 / 2 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 1 / 0 | 1 / 0 / 0 | 0 / 0 / 0 |
| F1_S07_5 | 5 | 1 | 1 / 1 / 1 | 1 / 1 / 2 | 1 / 1 / 2 | 1 / 2 / 2 | 2 / 1 / 1 | 2 / 1 / 2 |
| F1_S08_5 | 5 | 0 | 1 / 0 / 1 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 1 / 0 / 0 | 0 / 1 / 0 |
| F1_S09_5 | 5 | 2 | 0 / 0 / 2 | 0 / 0 / 2 | 2 / 2 / 2 | 2 / 2 / 2 | 2 / 2 / 0 | 2 / 0 / 2 |
| F2_S17_5 | 5 | 1 | 1 / 1 / 1 | 1 / 0 / 1 | 0 / 1 / 1 | 1 / 0 / 1 | 1 / 1 / 1 | 0 / 1 / 0 |
| F1_S01_10 | 10 | 2 | 2 / 2 / 2 | 2 / 2 / 1 | 2 / 3 / 2 | 1 / 1 / 1 | 2 / 2 / 3 | 2 / 2 / 2 |
| F1_S05_10 | 10 | 9 | 9 / 10 / 10 | 10 / 9 / 10 | 10 / 9 / 10 | 10 / 8 / 10 | 9 / 9 / 9 | 9 / 9 / 9 |
| F1_S07_10 | 10 | 0 | 0 / 0 / 1 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| F1_S08_10 | 10 | 12 | 12 / 12 / 13 | 12 / 12 / 12 | 12 / 12 / 12 | 13 / 12 / 12 | 12 / 13 / 12 | 13 / 13 / 13 |
| F1_S09_10 | 10 | 0 | 0 / 0 / 0 | 0 / 1 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| F1_S12_10 | 10 | 12 | 13 / 11 / 11 | 11 / 11 / 13 | 11 / 11 / 11 | 11 / 11 / 11 | 11 / 11 / 11 | 11 / 11 / 12 |
| F2_S13_10 | 10 | 8 | 8 / 8 / 7 | 8 / 8 / 8 | 9 / 9 / 9 | 9 / 9 / 8 | 7 / 9 / 8 | 8 / 9 / 10 |
| F2_S15_10 | 10 | 6 | 6 / 6 / 6 | 6 / 6 / 7 | 6 / 6 / 6 | 6 / 6 / 6 | 6 / 6 / 6 | 7 / 6 / 7 |
| F2_S17_10 | 10 | 5 | 5 / 5 / 5 | 5 / 5 / 5 | 5 / 5 / 6 | 6 / 5 / 7 | 5 / 5 / 6 | 4 / 5 / 5 |
| F2_S20_10 | 10 | 34 | 35 / 39 / 35 | 34 / 34 / 34 | 33 / 34 / 33 | 32 / 33 / 32 | 33 / 39 / 36 | 35 / 33 / 33 |
| F2_S21_10 | 10 | 1 | 3 / 4 / 4 | 1 / 1 / 1 | 1 / 5 / 1 | 3 / 4 / 1 | 1 / 1 / 3 | 3 / 3 / 4 |
| F2_S22_10 | 10 | 3 | 3 / 4 / 4 | 2 / 4 / 2 | 3 / 5 / 3 | 4 / 5 / 3 | 3 / 3 / 5 | 4 / 4 / 2 |
| F2_S23_10 | 10 | 0 | 0 / 0 / 2 | 2 / 0 / 3 | 1 / 1 / 0 | 0 / 1 / 0 | 0 / 1 / 2 | 2 / 0 / 1 |

## 4. Videos that were recorded slow

Every video of the split as recorded, by the frame rate of its file. These are other people and other cameras, so this table cannot tell the frame rate from the person; sections 1-3 can, because there the same video is compared with itself.

| Group | Videos | Subjects | `0` videos | Hours scored | Drowsiness false alarms | / h | `10` videos | with an alert |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ≥ 15 FPS | 67 | 23 | 23 | 3.67 | 5 | 1.36 | 22 | 12 |
| < 15 FPS | 5 | 2 | 1 | 0.20 | 2 | 10.13 | 2 | 2 |
