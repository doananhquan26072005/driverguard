# DriverGuard - evaluation on UTA-RLDD (video labels 0 / 5 / 10)

UTA-RLDD (Ghoddoosian et al., CVPRW 2019), Kaggle copy `rishab260/uta-reallife-drowsiness-dataset`: 48 subjects
(folds 1-4), 145 videos, 25.0 h, 2 435 120 frames. One self-rated label per video: 0 = alert, 5 = low vigilance,
10 = drowsy. Subjects sit in front of a laptop, they do not drive. Real drowsiness, not acted.

How it was run (06/10/2026):

- Blocks 2-12 traced once per video on Kaggle (`notebooks/uta_rldd_kaggle.ipynb`, two sessions, ~16 h of
  tracing at ~42 frames/s on 4 CPU workers), code at commit `e57632c`, MediaPipe 1.0.1, phone model off,
  simulated 60 km/h, fresh state per video. No video failed. Traces hold numbers only.
- Every number below comes from blocks 7-12 replayed on those traces with the same commit. Replay gives the same
  number of alerts as the traced run on all dev videos.
- Scores, levels and windows leave out the first 30 s of each video (`eval.warmup_s`).
- **Split by subject:** dev = folds 1-2 (24 subjects), test = folds 3-4 (24 subjects). Thresholds were searched on
  dev only. The test folds were scored once, for the current thresholds and for the one chosen configuration.
- False alarm = an alert of the drowsiness branch on a `0` video after the start-up stretch. Exact Poisson 95 % CI.
  Distraction alerts (off_road) are counted apart: the subjects look at a laptop.

Limits to keep in mind: the label covers a whole video (a `10` video is not drowsy on every second, a `0` video
may hold sleepy stretches), it is self-rated, and nobody drives. Not the PRD verdict; a check before real drives.
MediaPipe on Kaggle (1.0.1) is not the version of the other reports (0.10.21), same model file.

## 1. Thresholds before M53 (commit e57632c)

| | Dev (folds 1-2) | Test (folds 3-4) |
|---|---:|---:|
| Awake hours scored | 3.87 | 4.08 |
| Drowsiness false alarms | 9 | 8 |
| per hour (95 % CI) | 2.33 (1.06–4.42) | 1.96 (0.85–3.87) |
| of them L2 or L3 / L3 | 3 / 1 | 3 / 2 |
| Subjects with a false-alarm window, of 24 | 4 | 3 |
| Window FAR, ≥ L1 / ≥ L2 (10 s windows on `0`) | 9.0 % / 0.4 % | 3.9 % / 0.4 % |
| Highest window FAR of one subject | 69.0 % | 69.0 % |
| Windows ≥ L1 on `10` / on `5` | 38.3 % / 16.5 % | 49.2 % / 31.2 % |
| AUC of mean drowsy_score, `10` vs `0` | 0.793 | 0.917 |
| Same subject, score higher at `10` than at `0` | 22 of 24 | 22 of 24 |
| `10` videos with ≥ 1 drowsiness alert / at L2+ / at L3 | 16 / 12 / 12 of 24 | 17 / 14 / 12 of 24 |
| `5` videos with ≥ 1 drowsiness alert / an L3 | 10 / 4 of 24 | 13 / 9 of 24 |
| Distraction alerts on `0` | 4 | 0 |

- The PRD target (≤ 1.0 false alarms / h, CI included) is not shown: the upper bounds are 4.4 and 3.9 / h.
- The false alarms sit on few subjects (dev: S01, S15, S23, S24; test: S31, S44, S48). S15, S24 and S44 score at
  `0` close to their own `10`: possibly sleepy while recording the "alert" video. Not checked on the videos.
- The system does follow the level: within a subject the score is higher at `10` than at `0` for 22 of 24, on
  both splits.

## 2. Which signals follow the drowsiness level

One number per video, per subject; AUC `10` vs `0`, and how many subjects move in the drowsy direction between
their own `0` and `10`.

| Signal | Dev AUC | Dev paired | Test AUC | Test paired |
|---|---:|---:|---:|---:|
| drowsy_score term: PERCLOS (weight 40) | 0.816 | 20 / 4 | 0.870 | 21 / 1 |
| drowsy_score term: microsleep (25) | 0.788 | 15 / 0 | 0.799 | 15 / 0 |
| drowsy_score term: yawn (15) | 0.588 | 5 / 1 | 0.667 | 8 / 0 |
| drowsy_score term: nod (20) | 0.456 | 0 / 3 | 0.582 | 5 / 1 |
| drowsy_score term: slow blink (10) | 0.523 | 13 / 11 | 0.628 | 14 / 8 |
| drowsy_score term: brow raise (10) | 0.536 | 4 / 3 | 0.606 | 6 / 3 |
| Frames with EAR < 0.65 x baseline (current PERCLOS rule) | 0.812 | 22 / 2 | 0.892 | 24 / 0 |
| Frames with EAR < 0.48 x baseline (~ P80) | 0.814 | 22 / 2 | 0.873 | 22 / 2 |
| Frames with MediaPipe eyeBlink ≥ 0.5 | 0.818 | 23 / 1 | 0.885 | 23 / 1 |
| Longest closed_duration | 0.866 | 23 / 1 | 0.872 | 23 / 1 |
| Block 7 blink duration, median | 0.653 | 16 / 8 | 0.677 | 16 / 8 |
| Block 7 eyelid reopening time, median | 0.648 | 16 / 8 | 0.656 | 16 / 8 |

- PERCLOS and microsleep carry the score. Slow blink and brow raise do not separate within subjects (sign test
  p = 0.84 and 1.0 on dev, 0.29 and 0.51 on test). Nod events are rare on both sides (subjects are not driving).
- PERCLOS by the P80 closure (0.48) separates no better than the current closure (0.65): no reason here to change
  `perclos_close_ratio`.
- Blink duration and reopening time: weak (16 of 24 subjects, p = 0.15, on both splits). Same direction as the
  FL3D prototype (`blink_duration_fl3d.md`): not worth a `duration_ratio`.
- `gaze_down` (block 7) is on for ~0 % of the time at every level: its side effect on drowsy subjects cannot be
  measured on this dataset.

## 3. Threshold search on dev (51 + 6 configurations)

One or two keys changed at a time (`tools/uta_rldd.py grid`, 51 configurations), then 6 combinations of the best single changes. Microsleep /
L3 thresholds were not searched: the dataset does not say where the microsleeps are.

| Configuration (dev) | False alarms | per hour (95 % upper) | FAR L1 | AUC | `10` alerted |
|---|---:|---:|---:|---:|---:|
| Current | 9 | 2.33 (4.42) | 9.0 % | 0.793 | 16 / 24 |
| A: weight_slow_blink = 0, weight_brow = 0 | 8 | 2.07 (4.08) | 8.0 % | 0.859 | 14 / 24 |
| **B: A + risk.trend.level = 0** | 5 | 1.29 (3.02) | 3.7 % | 0.859 | 14 / 24 |
| C: B + risk.drowsy.l1 = 50 | 2 | 0.52 (1.87) | 0.7 % | 0.859 | 12 / 24 |
| risk.trend.level = 0 alone | 6 | 1.55 (3.38) | 5.6 % | 0.793 | 15 / 24 |
| perclos_low / high = 0.15 / 0.40 | 4 | 1.03 (2.65) | 3.7 % | 0.769 | 14 / 24 |
| weight_perclos = 0 | 4 | 1.03 (2.65) | 3.8 % | 0.760 | 14 / 24 |
| weight_microsleep = 0 | 9 | 2.33 (4.42) | 6.7 % | 0.733 | 14 / 24 |
| weight_nod = 0 | 8 | 2.07 (4.08) | 7.1 % | 0.804 | 16 / 24 |
| weight_yawn = 0 | 9 | 2.33 (4.42) | 9.0 % | 0.781 | 16 / 24 |
| perclos_close_ratio = 0.48 | 8 | 2.07 (4.08) | 8.6 % | 0.766 | 14 / 24 |

Yawn thresholds, `perclos_drowsy`, `l2`, `bowed_pitch_deg = 0`, `l1_repeat_count = 0`: no change, or only on L2.
No configuration brings the upper bound to 1.0 / h: on 3.87 h that needs 0 false alarms.

## 4. Chosen configuration B, on the held-out folds (scored once)

B = `risk.drowsy.weight_slow_blink: 0`, `risk.drowsy.weight_brow: 0`, `risk.trend.level: 0`.

| Test (folds 3-4), 4.08 awake hours | Current | B |
|---|---:|---:|
| Drowsiness false alarms | 8 | 4 |
| per hour (95 % CI) | 1.96 (0.85–3.87) | 0.98 (0.27–2.51) |
| of them L2 or L3 / L3 | 3 / 2 | 2 / 2 |
| Subjects with a false-alarm window, of 24 | 3 | 1 |
| Window FAR, ≥ L1 / ≥ L2 | 3.9 % / 0.4 % | 1.5 % / 0.2 % |
| Highest window FAR of one subject | 69.0 % | 37.9 % |
| Windows ≥ L1 on `10` / on `5` | 49.2 % / 31.2 % | 40.8 % / 18.2 % |
| AUC of mean drowsy_score, `10` vs `0` | 0.917 | 0.924 |
| Same subject, score higher at `10` than at `0` | 22 of 24 | 22 of 24 |
| `10` videos with ≥ 1 drowsiness alert / at L2+ / at L3 | 17 / 14 / 12 of 24 | 15 / 12 / 12 of 24 |
| `5` videos with ≥ 1 drowsiness alert / an L3 | 13 / 9 of 24 | 12 / 9 of 24 |

- Half the false alarms, on test as on dev (dev: 9 → 5). All 4 left on test are one subject (S44: 2 L1
  drowsy_score, 2 L3 microsleep); the L3 ones are outside what B changes.
- Cost: 2 of 24 drowsy subjects lose their only alert on each split (dev 16 → 14, test 17 → 15). L3 detections
  are unchanged (12 of 24 on both).
- Still not the PRD target: 0.98 / h, upper bound 2.51 / h.

EU DDAW frame, approximation only (`10` ≈ KSS ≥ 8, one event per subject, detected = ≥ 1 drowsiness alert on the
`10` video; Wilson 90 % CI). DDAW asks for a mean > 40 % and a 90 % lower bound > 20 %.

| | Current | B |
|---|---:|---:|
| Dev | 66.7 % (49.9–80.1) | 58.3 % (41.8–73.2) |
| Test | 70.8 % (54.1–83.3) | 62.5 % (45.8–76.7) |

## 5. B on the earlier datasets (must not get worse)

Blocks 5, 7-12 replayed on the stored traces (`fl3d_v2`, `yawdd_v2`, `sust_v2`) with the code of 06/10 (M38-M52
in), before and after the three keys changed.

| Dataset | Before → B |
|---|---|
| FL3D | Microsleep alerts unchanged (83 hits, 1 false); repeated L3 unchanged (62 hits, 1 false). L1 alerts 9 → 10 (hits 8 → 9, false 1 → 1); L2 alerts 19 → 16 (hits 15 → 13, false 3 → 3) |
| YawDD | Report identical |
| SUST | Report identical |

Nothing gets worse on microsleep / L3. FL3D loses 2 correct L2 alerts (the score no longer reaches L2 on two
videos without the slow-blink / brow terms); its false alarms stay as they were. The stored reports
`dataset_fl3d.md`, `dataset_yawdd.md`, `dataset_sust_ddd.md` were not regenerated.

## 6. Measurability

- Face found on ≥ 99 % of frames at every level (dev). Reliable face below 80 % of frames on 2 of 145 videos:
  F2_S23_0 (77.6 %), F4_S42_10 (73.4 %).
- The eye CNN decided on 0.4 % (`0`) to 9.8 % (`5`) of dev frames; the rest is EAR.
- FPS from 12 to 30 across videos; resolutions from 240x426 to 2560x1440, portrait and landscape.

## 7. Does a per-driver baseline help? (after M53)

`personalization_uta_rldd.md`: the same videos with a fixed common eye baseline, the self-learnt one, and a fake
driver enrollment (from the start of the same video, or from the start of the subject's own `0` video).

| 48 subjects, 7.94 awake hours | False alarms | per hour (95 % upper) | FAR L1 | AUC | `10` alerted |
|---|---:|---:|---:|---:|---:|
| Fixed common baseline | 7 | 0.88 (1.82) | 2.4 % | 0.900 | 28 / 48 |
| Self-learnt (as evaluated) | 9 | 1.13 (2.15) | 2.6 % | 0.888 | 29 / 48 |
| Fake-enrolled, same video | 9 | 1.13 (2.15) | 2.6 % | 0.885 | 28 / 48 |
| Fake-enrolled, the subject's `0` video | 9 | 1.13 (2.15) | 2.6 % | 0.891 | 29 / 48 |

- No setting lowers false alarms against the self-learnt baseline: 9, 9, 9. The fixed baseline has 2 fewer on
  dev and the same 4 on test; inside the CIs.
- The alert-state baseline (best case of M9) raises the share of `10` windows at ≥ L1 a little (33.1 → 35.6 %)
  and nothing else. Not a measured benefit: "personalised" stays out of the reports, as on YawDD.
- No eyewear attribute in the Kaggle copy, so no glasses split.

## Status

Applied in M53 (06/10/2026): `risk.drowsy.weight_slow_blink` 10 → 0, `risk.drowsy.weight_brow` 10 → 0,
`risk.trend.level` 1 → 0 (note only). Sections 1-4 were measured on commit `e57632c`; replayed again on the
code of 06/10 (M38-M52, M54 in) they give the same false alarms, FAR and alerted subjects before and after the
change, also with block 5 decided again under M54's `eye_state.low_light_brightness: 0` (the traces were made
with 60; `--eye block5`, the default of the tool; AUC moves in the third decimal). Reproduce from the stored
traces (`data/eval_traces/uta_rldd/`, not in the repo):

    python tools/uta_rldd.py report --split dev
    python tools/uta_rldd.py compare --split test --set risk.drowsy.weight_slow_blink=10 --set risk.drowsy.weight_brow=10 --set risk.trend.level=1
    python tools/uta_rldd.py grid
    python tools/uta_rldd.py personal --out eval/results/personalization_uta_rldd.md

Not decided here: `perclos_close_ratio` (P80 no better), `risk.drowsy.l1` (50 halves the dev false alarms again
and loses 2 more drowsy subjects; not scored on test), the nod and yawn weights (rare events at a laptop).
