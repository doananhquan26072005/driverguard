# DriverGuard - results by lighting and eyewear

Blocks 7-12 replayed on the stored traces (`tools/trace_studies.py lighting`); nothing was re-recorded. Face brightness = mean luminance (0-255) of the face before CLAHE, the number block 5 uses (`eye_state.low_light_brightness` = 60: below it EAR is not trusted and the eye CNN decides). A video goes in the bin of its median face brightness (`eval.brightness_bins` = [60, 100, 140]).

**Do not compare across datasets.** Each dataset is other people, another camera and another kind of acting; a darker group in one dataset is not "the same drivers in less light". Inside a dataset the groups are still different people. The like-for-like answer, the same videos darkened / overexposed / blurred in RAM, is in eval/results/lighting_transforms.md (`tools/light_study.py`).

False alarms: alerts on clips without drowsiness (SUST not drowsy, YawDD normal / talking; FL3D: alerts on frames labelled `alert`, more than 3 s from any microsleep / yawning run), per hour of such time, exact Poisson 95 % CI. Few minutes per group: most intervals are wide.

## fl3d: by face brightness

FL3D / NITYMED: night driving, acted, 25 FPS, frame labels.

| Group | Videos | Min | Face found | CNN-decided frames | Unavailable | False alarms / hour (95% CI) | Hours they are on | Microsleep runs reaching L3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 60–100 | 44 | 47.2 | 98.1% | 7.5% | 0.0% | 9.2 (2.52–23.7) | 0.43 | 75/95 (78.9%) |

## yawdd: by face brightness

YawDD mirror camera: parked car, daylight, clip labels.

| Group | Videos | Min | Face found | CNN-decided frames | Unavailable | False alarms / hour (95% CI) | Hours they are on | Yawning clips with a yawn event |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| < 60 | 9 | 2.7 | 98.9% | 98.5% | 0.0% | 0.0 (0.00–115.7) | 0.03 | 2/3 (66.7%) |
| 60–100 | 69 | 27.7 | 99.3% | 21.2% | 0.0% | 6.2 (0.75–22.3) | 0.32 | 21/24 (87.5%) |
| 100–140 | 205 | 79.7 | 99.3% | 22.6% | 0.0% | 5.3 (1.73–12.4) | 0.94 | 63/73 (86.3%) |
| ≥ 140 | 36 | 13.8 | 99.1% | 21.5% | 0.0% | 19.7 (4.07–57.7) | 0.15 | 8/14 (57.1%) |

## sust: by face brightness

SUST-DDD: phone camera, real driving, 10 s clips, clip labels.

| Group | Videos | Min | Face found | CNN-decided frames | Unavailable | False alarms / hour (95% CI) | Hours they are on | Drowsy clips with an alert |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| < 60 | 17 | 2.8 | 100.0% | 96.7% | 0.0% | 0.0 (0.00–147.6) | 0.03 | 0/8 (0.0%) |
| 60–100 | 144 | 24.0 | 99.0% | 10.7% | 0.0% | 7.1 (0.86–25.8) | 0.28 | 0/43 (0.0%) |
| 100–140 | 1185 | 197.6 | 98.9% | 5.4% | 0.0% | 9.7 (5.64–15.5) | 1.76 | 5/553 (0.9%) |
| ≥ 140 | 728 | 121.4 | 97.6% | 6.4% | 0.3% | 8.1 (3.48–15.9) | 0.99 | 11/371 (3.0%) |

### fl3d: eyes closed per frame, by the brightness of that frame

Block 7 `eye_closed` against FL3D `microsleep` / `alert` frames. Frames, not videos, are binned here.

| Face brightness | Frames | Precision | Recall | FPR | CNN-decided |
|---|---:|---:|---:|---:|---:|
| < 60 | 466 | 99.4% | 40.3% | 2.4% | 100.0% |
| 60–100 | 46448 | 71.6% | 92.6% | 7.8% | 8.8% |
| 100–140 | 5 | – | – | 0.0% | 0.0% |
| unknown | 915 | – | 0.0% | 0.0% | 0.0% |

## yawdd: by eyewear (from the file names)

`NoGlasses` / `Glasses` / `SunGlasses` in the file name. The other datasets carry no such attribute.

| Group | Videos | Min | Face found | CNN-decided frames | Unavailable | False alarms / hour (95% CI) | Hours they are on | Yawning clips with a yawn event |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| no glasses | 181 | 70.3 | 99.3% | 14.9% | 0.0% | 4.8 (1.32–12.4) | 0.82 | 52/65 (80.0%) |
| glasses | 102 | 40.9 | 99.3% | 26.1% | 0.0% | 10.5 (3.42–24.6) | 0.47 | 31/36 (86.1%) |
| sunglasses | 36 | 12.8 | 98.8% | 66.7% | 0.0% | 6.7 (0.17–37.2) | 0.15 | 11/13 (84.6%) |

False alarms by reason: glasses: L2 off_road 4, L3 microsleep 1; no glasses: L2 off_road 4; sunglasses: L2 off_road 1.

## What is not covered

- Faces darker than the low-light threshold (60) are rare here: only the `< 60` rows above, a few minutes in all (FL3D night clips are lit to 70-90). Infrared, backlight and glare: no video; `is_ir` is 0 on every trace.
- Day / night per clip is not labelled in YawDD or SUST; FL3D is all night.
- Sunglasses: YawDD has a few clips, but its labels are yawning only, so they say nothing about closed eyes behind dark lenses (NTHU-DDD is the set for that).
