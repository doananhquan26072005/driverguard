# DriverGuard - the same videos in other light

`tools/light_study.py`: every frame is darkened, overexposed, turned grey or blurred in RAM before block 2, then blocks 2-12 run as usual. A row differs from `original` by the transform alone (same people, same camera, same acting), which eval/results/lighting.md could not say. No image is written.

- `gamma g`: 255 x (in / 255) ^ g, darker. `gain k`: in x k clipped at 255, overexposed (whole image).
- `grey`: channels replaced by the luminance; block 2 then calls the image infrared and block 5's eye CNN decides. `blur s`: Gaussian blur, sigma s pixels at 640 px width.
- Face brightness / sharpness: medians of the block 6 quality numbers on frames with a face (mean luminance 0-255 before CLAHE; Laplacian variance).
- Unavailable: share of frames with monitoring unavailable and why (`risk.unavailable`: no face 3.0 s, unusable face 5.0 s; `quality`: dark < 25, glare > 225, blur < 3.0).
- False alerts: as in lighting.md (FL3D: on `alert` frames more than 3 s from a drowsy run; YawDD: on normal / talking clips), the count in brackets.

**Limits.** Synthetic changes: no sensor noise of a dark cabin, no real infrared image, no sun patch on half a face. A few videos per dataset, so the detection columns move by one or two events. This shows where the pipeline stops working, not how often such light occurs on the road.

## fl3d

FL3D / NITYMED: night driving, acted, 25 FPS, frame labels. 8 videos, 8.3 min per transform.

| Transform | Face found | Face brightness | Sharpness | CNN-decided | Unavailable (why) | Microsleep runs reaching L3 | Eyes closed: recall | FPR | False alerts / hour (95% CI) |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|
| original | 97.6% | 82 | 80.3 | 7.3% | 0.0% | 18/24 (75.0%) | 88.6% | 8.9% | 0.0 (0.00–37.8) [0] |
| gamma 1.5 | 97.6% | 49 | 60.6 | 8.7% | 0.0% | 12/24 (50.0%) | 82.2% | 8.0% | 0.0 (0.00–37.8) [0] |
| gamma 2.2 | 96.7% | 25 | 32.1 | 11.2% | 29.8% (low_light 29.6%, bad_angle 0.3%) | 3/24 (12.5%) | 63.9% | 5.7% | 0.0 (0.00–37.8) [0] |
| gamma 3.5 | 90.6% | 8 | 8.7 | 15.4% | 82.7% (low_light 81.3%, bad_angle 1.4%) | 0/24 (0.0%) | 24.4% | 4.9% | 0.0 (0.00–37.8) [0] |
| gamma 5 | 48.5% | 3 | 2.4 | 12.2% | 55.6% (low_light 43.1%, camera_blocked 11.2%, bad_angle 1.4%) | 0/24 (0.0%) | 5.4% | 2.7% | 10.2 (0.26–57.1) [1] |
| gain 1.5 | 97.5% | 122 | 178.2 | 7.2% | 0.0% | 18/24 (75.0%) | 90.0% | 8.4% | 0.0 (0.00–37.8) [0] |
| gain 2.5 | 97.0% | 187 | 350.8 | 5.9% | 0.0% | 18/24 (75.0%) | 88.2% | 8.4% | 0.0 (0.00–37.8) [0] |
| gain 4 | 90.1% | 230 | 223.3 | 5.7% | 49.4% (glare 48.9%, bad_angle 0.5%) | 9/24 (37.5%) | 77.7% | 9.7% | 0.0 (0.00–37.8) [0] |
| grey | 96.4% | 81 | 80.2 | 100.0% | 0.0% | 0/24 (0.0%) | 9.4% | 1.3% | 0.0 (0.00–37.8) [0] |
| blur 1.5 | 97.7% | 82 | 5.1 | 13.7% | 0.0% | 17/24 (70.8%) | 83.3% | 13.9% | 10.2 (0.26–57.1) [1] |
| blur 3 | 95.7% | 82 | 2.3 | 29.9% | 87.9% (blur 86.4%, bad_angle 1.4%) | 0/24 (0.0%) | 49.8% | 18.4% | 0.0 (0.00–37.8) [0] |
| blur 6 | 34.8% | 82 | 1.8 | 6.2% | 29.4% (no_face 12.7%, blur 12.2%, bad_angle 4.5%) | 0/24 (0.0%) | 0.1% | 1.2% | 30.7 (6.34–89.8) [3] |

## yawdd

YawDD mirror camera: parked car, daylight, clip labels. 8 videos, 2.4 min per transform.

| Transform | Face found | Face brightness | Sharpness | CNN-decided | Unavailable (why) | Yawning clips with a yawn event | False alerts / hour (95% CI) |
|---|---:|---:|---:|---:|---|---:|---:|
| original | 100.0% | 115 | 212.1 | 22.5% | 0.0% | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| gamma 1.5 | 100.0% | 85 | 257.7 | 23.8% | 0.0% | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| gamma 2.2 | 100.0% | 59 | 290.2 | 25.1% | 0.0% | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| gamma 3.5 | 99.7% | 35 | 314.0 | 26.8% | 5.9% (low_light 5.9%) | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| gamma 5 | 99.4% | 21 | 317.6 | 30.2% | 37.4% (low_light 37.4%) | 2/4 (50.0%) | 0.0 (0.00–161.1) [0] |
| gain 1.5 | 99.8% | 164 | 351.2 | 20.9% | 0.0% | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| gain 2.5 | 96.0% | 219 | 343.2 | 14.0% | 28.1% (glare 28.1%) | 0/4 (0.0%) | 0.0 (0.00–161.1) [0] |
| gain 4 | 82.6% | 237 | 244.6 | 7.5% | 63.8% (glare 60.3%, no_face 2.7%, bad_angle 0.8%) | 0/4 (0.0%) | 0.0 (0.00–161.1) [0] |
| grey | 100.0% | 115 | 211.1 | 100.0% | 0.0% | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| blur 1.5 | 100.0% | 116 | 10.3 | 19.7% | 0.0% | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| blur 3 | 99.5% | 117 | 3.0 | 16.3% | 32.4% (blur 32.4%) | 3/4 (75.0%) | 0.0 (0.00–161.1) [0] |
| blur 6 | 91.0% | 116 | 2.0 | 23.8% | 66.7% (blur 65.4%, no_face 1.2%, bad_angle 0.0%) | 0/4 (0.0%) | 0.0 (0.00–161.1) [0] |
