# DriverGuard - UTA-RLDD, frame times of the video files

18 video files below the folder given (145 videos are traced). Source: commit 7838845 (uncommitted changes); thresholds.yaml sha256 c7659a57191e.

`By index` is frames / container FPS, the time every trace made before M86 was scored on. `Clock` is the container's timestamp of the last frame plus one nominal frame, what traces are made on from M86. `Drift` is the difference between the two at the end of the video, `Largest offset` the biggest difference at any frame: the container FPS is an average, so a stretch without frames moves every frame time around it without changing the total. A long gap is a wait of at least 2 nominal frames between two frames (`eval.clock_long_gap_frames`). Unit: one video file.

- Videos read: 18 of 18 (308364 frames).
- Timestamps the container did not give, replaced by one nominal frame: 0 frames in 0 videos.
- Videos with at least one long gap: 2; long gaps in all: 5.
- |clock − by index| at the end of the video: median 0.00 s, largest 0.07 s.
- Largest offset at any frame: median 0.00 s, largest 1.54 s; videos where it reaches 1 s: 1.
- Videos below 15 FPS (`eval.min_video_fps`): 0.

| Video | Frames | FPS | By index (s) | Clock (s) | Drift (s) | Largest offset (s) | Gap p50 (ms) | Gap p95 (ms) | Gap max (ms) | Long gaps | Patched |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| F1_S06_10 | 10233 | 23.820 | 429.60 | 429.60 | +0.00 | 1.54 | 41.8 | 41.9 | 2631.1 | 3 | 0 |
| F1_S06_0 | 15230 | 24.962 | 610.12 | 610.12 | -0.00 | 0.22 | 40.1 | 40.3 | 45.8 | 0 | 0 |
| F1_S03_10 | 18480 | 29.995 | 616.10 | 616.13 | +0.03 | 0.09 | 33.3 | 33.3 | 66.7 | 0 | 0 |
| F1_S03_5 | 18514 | 29.989 | 617.37 | 617.43 | +0.07 | 0.07 | 33.3 | 33.3 | 100.0 | 2 | 0 |
| F1_S06_5 | 13117 | 29.907 | 438.59 | 438.59 | +0.00 | 0.05 | 33.4 | 33.6 | 45.1 | 0 | 0 |
| F1_S01_0 | 18053 | 29.969 | 602.39 | 602.39 | +0.00 | 0.00 | 33.3 | 33.3 | 35.0 | 0 | 0 |
| F1_S01_10 | 18011 | 29.969 | 600.99 | 600.99 | +0.00 | 0.00 | 33.4 | 33.4 | 33.4 | 0 | 0 |
| F1_S01_5 | 17969 | 29.969 | 599.59 | 599.59 | +0.00 | 0.00 | 33.4 | 33.4 | 33.4 | 0 | 0 |
| F1_S02_0 | 18263 | 29.969 | 609.40 | 609.40 | +0.00 | 0.00 | 33.3 | 33.3 | 35.0 | 0 | 0 |
| F1_S02_10 | 18124 | 29.969 | 604.76 | 604.76 | +0.00 | 0.00 | 33.3 | 33.3 | 35.0 | 0 | 0 |
| F1_S02_5 | 18103 | 29.969 | 604.06 | 604.06 | +0.00 | 0.00 | 33.3 | 33.3 | 35.0 | 0 | 0 |
| F1_S03_0 | 20763 | 29.969 | 692.82 | 692.82 | +0.00 | 0.00 | 33.3 | 33.3 | 35.0 | 0 | 0 |
| F1_S04_0 | 15364 | 25.000 | 614.56 | 614.56 | +0.00 | 0.00 | 40.0 | 40.0 | 40.0 | 0 | 0 |
| F1_S04_10 | 15394 | 25.000 | 615.76 | 615.76 | +0.00 | 0.00 | 40.0 | 40.0 | 40.0 | 0 | 0 |
| F1_S04_5 | 18224 | 30.000 | 607.47 | 607.47 | +0.00 | 0.00 | 33.3 | 33.3 | 33.3 | 0 | 0 |
| F1_S05_0 | 18410 | 30.025 | 613.16 | 613.16 | -0.00 | 0.00 | 33.3 | 33.3 | 33.3 | 0 | 0 |
| F1_S05_10 | 18050 | 30.025 | 601.17 | 601.17 | -0.00 | 0.00 | 33.3 | 33.3 | 33.3 | 0 | 0 |
| F1_S05_5 | 18062 | 30.025 | 601.57 | 601.57 | -0.00 | 0.00 | 33.3 | 33.3 | 33.3 | 0 | 0 |
