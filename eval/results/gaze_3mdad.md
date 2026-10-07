# DriverGuard - looking down, looking away and closed eyes on 3MDAD

50 drivers (47 with usable safe-driving frames), 111017 frames, 16 actions each, real car, face camera, daytime. Blocks 2-12 with config/thresholds.yaml, each driver's actions joined into one drive (safe driving first). Assumed frame rate: 30 FPS (not stored with the frames).

Every signal is taken against the same driver's safe-driving frames: EAR as a ratio of that median, iris_y, pitch and yaw as a difference (iris_y: iris centre against the line through the eye corners, in eye widths, > 0 = lower). A label covers the whole sequence of an action, also the frames where the driver reaches for the phone or looks back at the road. Acted. Numbers only, no image stored.

## 1. The signals per action (frames with a face; p10 / p50 / p90 over all drivers)

Deep by today's rule: EAR ≤ 0.5 x the driver's safe-driving EAR and eyeBlink ≥ 0.5, what block 7 counts toward a microsleep.

| Action | Frames | Face found | EAR ratio | eyeBlink | eyeLookDown | iris_y | Pitch | Yaw (abs) | Deep by today's rule | Phone in the driver zone |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AC1 safe driving | 6475 | 88% | 0.67 / 0.97 / 1.14 | 0.05 / 0.16 / 0.39 | 0.09 / 0.33 / 0.66 | -0.03 / 0.00 / 0.05 | -3.97 / -0.06 / 4.19 | 0.32 / 2.27 / 11.50 | 2.8% | 0% |
| AC2 hair / makeup | 6133 | 62% | 0.78 / 1.15 / 1.65 | 0.02 / 0.10 / 0.32 | 0.04 / 0.23 / 0.58 | -0.09 / -0.01 / 0.05 | -8.09 / 2.05 / 13.61 | 1.35 / 6.97 / 18.22 | 1.8% | 0% |
| AC3 adjusting the radio | 6176 | 96% | 0.28 / 0.63 / 1.08 | 0.06 / 0.31 / 0.60 | 0.10 / 0.46 / 0.76 | -0.01 / 0.06 / 0.11 | -1.77 / 5.20 / 14.56 | 5.26 / 14.98 / 24.15 | 20.2% | 0% |
| AC4 operating the GPS | 7229 | 59% | 0.60 / 0.90 / 1.15 | 0.04 / 0.14 / 0.39 | 0.06 / 0.33 / 0.66 | -0.04 / 0.01 / 0.06 | -6.98 / -0.80 / 7.39 | 1.71 / 10.10 / 21.84 | 3.2% | 0% |
| AC5 writing a message, right hand | 6039 | 95% | 0.18 / 0.53 / 1.11 | 0.06 / 0.40 / 0.67 | 0.10 / 0.59 / 0.80 | -0.02 / 0.08 / 0.14 | -1.11 / 6.04 / 13.21 | 1.32 / 7.16 / 18.26 | 36.8% | 36% |
| AC6 writing a message, left hand | 6045 | 78% | 0.38 / 0.87 / 1.29 | 0.06 / 0.28 / 0.54 | 0.09 / 0.47 / 0.72 | -0.03 / 0.04 / 0.13 | -3.36 / 4.96 / 13.20 | 1.27 / 5.70 / 14.77 | 12.5% | 1% |
| AC7 phone call, right hand | 7025 | 42% | 0.48 / 0.88 / 1.14 | 0.05 / 0.17 / 0.41 | 0.06 / 0.22 / 0.59 | -0.02 / 0.03 / 0.09 | 0.37 / 8.15 / 16.12 | 0.87 / 4.74 / 15.34 | 5.1% | 7% |
| AC8 phone call, left hand | 7121 | 84% | 0.50 / 0.87 / 1.15 | 0.05 / 0.18 / 0.45 | 0.07 / 0.30 / 0.63 | -0.03 / 0.02 / 0.07 | -7.04 / 0.54 / 8.38 | 0.82 / 4.75 / 15.08 | 5.5% | 3% |
| AC9 taking a picture | 6937 | 75% | 0.38 / 0.81 / 1.14 | 0.06 / 0.23 / 0.54 | 0.14 / 0.45 / 0.72 | -0.02 / 0.04 / 0.10 | -7.21 / 1.60 / 9.84 | 1.59 / 10.53 / 37.91 | 11.1% | 14% |
| AC10 talking to the passenger | 7996 | 75% | 0.44 / 0.85 / 1.29 | 0.05 / 0.19 / 0.49 | 0.11 / 0.41 / 0.69 | -0.04 / 0.03 / 0.08 | -7.05 / 0.88 / 9.07 | 3.66 / 22.10 / 67.78 | 7.1% | 2% |
| AC11 singing / dancing | 6935 | 69% | 0.45 / 0.76 / 1.09 | 0.08 / 0.24 / 0.46 | 0.14 / 0.41 / 0.67 | -0.02 / 0.03 / 0.08 | -9.56 / -0.09 / 9.58 | 1.15 / 7.07 / 25.55 | 5.9% | 0% |
| AC12 fatigue | 6508 | 63% | 0.34 / 0.75 / 1.14 | 0.07 / 0.28 / 0.59 | 0.14 / 0.47 / 0.79 | -0.02 / 0.04 / 0.11 | -9.24 / 1.48 / 14.95 | 0.93 / 4.89 / 14.98 | 15.7% | 0% |
| AC13 drinking, right hand | 6067 | 53% | 0.49 / 0.89 / 1.24 | 0.06 / 0.19 / 0.46 | 0.11 / 0.39 / 0.70 | -0.04 / 0.02 / 0.09 | -8.09 / 0.61 / 9.96 | 0.94 / 5.07 / 20.95 | 6.6% | 4% |
| AC14 drinking, left hand | 6014 | 63% | 0.59 / 0.94 / 1.27 | 0.07 / 0.20 / 0.44 | 0.12 / 0.38 / 0.68 | -0.05 / 0.01 / 0.07 | -7.52 / -0.18 / 8.10 | 0.87 / 5.44 / 18.10 | 3.7% | 0% |
| AC15 reaching behind | 5456 | 66% | 0.29 / 0.83 / 1.20 | 0.05 / 0.23 / 0.59 | 0.07 / 0.41 / 0.73 | -0.03 / 0.04 / 0.14 | -4.54 / 7.18 / 22.55 | 2.77 / 17.43 / 60.91 | 16.4% | 0% |
| AC16 smoking | 7353 | 72% | 0.51 / 0.92 / 1.26 | 0.04 / 0.16 / 0.45 | 0.07 / 0.32 / 0.66 | -0.04 / 0.02 / 0.08 | -7.36 / 1.88 / 11.63 | 0.94 / 5.87 / 21.50 | 5.8% | 3% |

## 2. What the system answers per action (alerts, at the assumed 30 FPS)

Drivers whose sequence of that action got at least one alert of the kind. L3 microsleep during a message is the false alarm of docs/improvements.md "looking down or eyes closed"; an alert in safe driving is a false alarm outright. Sequences last 3-5 s: an alert that needs 2 s has little room.

| Action | Drivers | Median length (s) | L3 microsleep | off_road | phone | any alert |
|---|---:|---:|---:|---:|---:|---:|
| AC1 safe driving | 50 | 4.2 | 1 / 50 (2%) | 0 / 50 (0%) | 0 / 50 (0%) | 1 / 50 (2%) |
| AC2 hair / makeup | 50 | 4.4 | 0 / 50 (0%) | 4 / 50 (8%) | 0 / 50 (0%) | 4 / 50 (8%) |
| AC3 adjusting the radio | 50 | 4.2 | 1 / 50 (2%) | 5 / 50 (10%) | 0 / 50 (0%) | 6 / 50 (12%) |
| AC4 operating the GPS | 50 | 5.0 | 2 / 50 (4%) | 8 / 50 (16%) | 0 / 50 (0%) | 10 / 50 (20%) |
| AC5 writing a message, right hand | 50 | 4.2 | 0 / 50 (0%) | 4 / 50 (8%) | 20 / 50 (40%) | 23 / 50 (46%) |
| AC6 writing a message, left hand | 50 | 4.1 | 0 / 50 (0%) | 1 / 50 (2%) | 0 / 50 (0%) | 1 / 50 (2%) |
| AC7 phone call, right hand | 50 | 4.8 | 0 / 50 (0%) | 9 / 50 (18%) | 2 / 50 (4%) | 11 / 50 (22%) |
| AC8 phone call, left hand | 50 | 4.8 | 0 / 50 (0%) | 3 / 50 (6%) | 0 / 50 (0%) | 3 / 50 (6%) |
| AC9 taking a picture | 50 | 4.9 | 0 / 50 (0%) | 1 / 50 (2%) | 1 / 50 (2%) | 3 / 50 (6%) |
| AC10 talking to the passenger | 50 | 5.3 | 0 / 50 (0%) | 18 / 50 (36%) | 0 / 50 (0%) | 18 / 50 (36%) |
| AC11 singing / dancing | 50 | 4.7 | 0 / 50 (0%) | 6 / 50 (12%) | 0 / 50 (0%) | 6 / 50 (12%) |
| AC12 fatigue | 50 | 4.3 | 0 / 50 (0%) | 4 / 50 (8%) | 0 / 50 (0%) | 4 / 50 (8%) |
| AC13 drinking, right hand | 50 | 4.1 | 0 / 50 (0%) | 3 / 50 (6%) | 0 / 50 (0%) | 3 / 50 (6%) |
| AC14 drinking, left hand | 50 | 4.2 | 0 / 50 (0%) | 2 / 50 (4%) | 0 / 50 (0%) | 2 / 50 (4%) |
| AC15 reaching behind | 50 | 3.7 | 0 / 50 (0%) | 10 / 50 (20%) | 0 / 50 (0%) | 10 / 50 (20%) |
| AC16 smoking | 50 | 4.8 | 0 / 50 (0%) | 3 / 50 (6%) | 0 / 50 (0%) | 3 / 50 (6%) |

## 3. The gaze-down angle as block 8 measures it, held for 2 s (at the assumed 30 FPS)

Blocks 5, 7-12 replayed with `distraction.gaze.down_deg` set to each value: head pitch off the road pose + `iris_gain` x (iris_y off the driver's usual value), frames block 7 calls firmly shut left out, the usual values learnt by the pipeline itself during the first seconds of the drive (safe driving). Drivers whose sequence of the action has `gaze_down_duration` ≥ 2 s. No alert reads this signal; the off_road and phone columns of section 2 are what the driver gets today.

| Action | ≥ 10° | ≥ 12° | ≥ 15° |
|---|---:|---:|---:|
| AC1 safe driving | 0 / 50 (0%) | 0 / 50 (0%) | 0 / 50 (0%) |
| AC2 hair / makeup | 0 / 50 (0%) | 0 / 50 (0%) | 0 / 50 (0%) |
| AC3 adjusting the radio | 12 / 50 (24%) | 10 / 50 (20%) | 7 / 50 (14%) |
| AC4 operating the GPS | 7 / 50 (14%) | 5 / 50 (10%) | 4 / 50 (8%) |
| AC5 writing a message, right hand | 13 / 50 (26%) | 7 / 50 (14%) | 6 / 50 (12%) |
| AC6 writing a message, left hand | 17 / 50 (34%) | 13 / 50 (26%) | 9 / 50 (18%) |
| AC7 phone call, right hand | 13 / 50 (26%) | 10 / 50 (20%) | 3 / 50 (6%) |
| AC8 phone call, left hand | 5 / 50 (10%) | 3 / 50 (6%) | 1 / 50 (2%) |
| AC9 taking a picture | 1 / 50 (2%) | 0 / 50 (0%) | 0 / 50 (0%) |
| AC10 talking to the passenger | 4 / 50 (8%) | 3 / 50 (6%) | 1 / 50 (2%) |
| AC11 singing / dancing | 2 / 50 (4%) | 1 / 50 (2%) | 0 / 50 (0%) |
| AC12 fatigue | 0 / 50 (0%) | 0 / 50 (0%) | 0 / 50 (0%) |
| AC13 drinking, right hand | 0 / 50 (0%) | 0 / 50 (0%) | 0 / 50 (0%) |
| AC14 drinking, left hand | 0 / 49 (0%) | 0 / 49 (0%) | 0 / 49 (0%) |
| AC15 reaching behind | 5 / 48 (10%) | 3 / 48 (6%) | 2 / 48 (4%) |
| AC16 smoking | 7 / 50 (14%) | 5 / 50 (10%) | 2 / 50 (4%) |

## 4. Writing a message against safe driving, driver by driver (AUC per frame)

One AUC per driver with at least 20 frames of both; 0.5 = the signal does not separate them.

| Signal | Drivers | Worst | p25 | Median | Pooled over drivers |
|---|---:|---:|---:|---:|---:|
| iris_y | 47 | 0.068 | 0.702 | 0.752 | 0.744 |
| look_down | 47 | 0.015 | 0.606 | 0.679 | 0.649 |
| pitch | 47 | 0.185 | 0.759 | 0.824 | 0.789 |
| ear_ratio | 47 | 0.055 | 0.621 | 0.687 | 0.676 |
