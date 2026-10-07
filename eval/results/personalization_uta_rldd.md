# DriverGuard - does a per-driver baseline help? (UTA-RLDD, config/thresholds.yaml; block 5 decided again from the traced inputs)

Blocks 7-12 replayed on the stored UTA-RLDD traces (`tools/uta_rldd.py personal`). Driver enrollment (M9) never runs in the evaluations (a simulated 60 km/h from the first frame), so its result is imitated: the medians of the good frames of the first seconds of a video (`eval.fake_enroll_s`) give the open-eye EAR, closed-mouth MAR and road pose, handed to blocks 7 and 8 the way a finished enrollment does.

- **fixed**: fixed common eye baseline (never learnt).
- **learnt**: self-learnt during the video (as evaluated).
- **own**: fake-enrolled from the start of the same video.
- **awake**: fake-enrolled from the start of the subject's `0` video.

`own` is what a real enrollment at the start of the trip would give (a drowsy driver enrolls drowsy). `awake` is the best case: the baseline of the same person when alert, used for their `5` and `10` videos (for a `0` video it is the same as `own`). The enrollment seconds lie inside the start-up stretch that no score counts. False alarms = drowsiness-branch alerts on `0` after the start-up stretch.

| Subjects | Setting | FAR L1 on 0 | FAR L2 on 0 | False alarms | / h | 95% upper | Worst subject FAR | AUC mean | AUC p90 | Pairs 10 > 0 | 10 alerted | 5 alerted | Windows ≥ L1 on 10 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| all (48) | fixed | 2.4% | 0.1% | 7 | 0.88 | 1.82 | 45.9% | 0.900 | 0.873 | 46 | 28 | 16 | 35.8% |
| all (48) | learnt | 2.6% | 0.1% | 9 | 1.13 | 2.15 | 45.9% | 0.888 | 0.864 | 44 | 29 | 17 | 33.1% |
| all (48) | own | 2.6% | 0.1% | 9 | 1.13 | 2.15 | 45.9% | 0.885 | 0.861 | 44 | 28 | 17 | 33.1% |
| all (48) | awake | 2.6% | 0.1% | 9 | 1.13 | 2.15 | 45.9% | 0.891 | 0.865 | 44 | 29 | 16 | 35.6% |
| dev (24) | fixed | 3.0% | 0.0% | 3 | 0.78 | 2.27 | 45.9% | 0.885 | 0.843 | 23 | 14 | 5 | 29.6% |
| dev (24) | learnt | 3.7% | 0.1% | 5 | 1.29 | 3.02 | 45.9% | 0.859 | 0.817 | 22 | 14 | 5 | 26.6% |
| dev (24) | own | 3.7% | 0.1% | 5 | 1.29 | 3.02 | 45.9% | 0.856 | 0.817 | 22 | 14 | 5 | 27.3% |
| dev (24) | awake | 3.7% | 0.1% | 5 | 1.29 | 3.02 | 45.9% | 0.863 | 0.820 | 22 | 14 | 5 | 29.9% |
| test (24) | fixed | 1.8% | 0.2% | 4 | 0.98 | 2.51 | 44.8% | 0.913 | 0.899 | 23 | 14 | 11 | 41.8% |
| test (24) | learnt | 1.5% | 0.2% | 4 | 0.98 | 2.51 | 37.9% | 0.920 | 0.903 | 22 | 15 | 12 | 39.3% |
| test (24) | own | 1.5% | 0.2% | 4 | 0.98 | 2.51 | 37.9% | 0.913 | 0.898 | 22 | 14 | 12 | 38.8% |
| test (24) | awake | 1.5% | 0.2% | 4 | 0.98 | 2.51 | 37.9% | 0.924 | 0.903 | 22 | 15 | 11 | 41.0% |

## Reading it

- One subject has one `0` video of ~10 min: the settings differ by a few alerts at most, and their CIs overlap. A small difference is not a result.
- The Kaggle copy carries no per-subject attributes (glasses), so there is no eyewear split here.
- The subjects sit at a laptop: the enrolled road pose is not tested by this dataset (distraction is scored apart from drowsiness everywhere above).
- Do not write "personalised" as a measured benefit in a report unless this table shows one.
