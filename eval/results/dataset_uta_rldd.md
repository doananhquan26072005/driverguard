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

**What the false-alarm number measures (read this before quoting "0.98 / h").** It is the *drowsiness-branch*
false alarm rate, not the PRD's "false alarms per hour" (the PRD counts every alert). It leaves out, besides the
distraction branch (section 9 counts it):

1. the first 30 s of every video (a driver hears those alerts too);
2. the checks this replay does not run: the traces have no frame-quality or iris columns, so the "monitoring
   paused" gate (M43) and the gaze direction (M55) never act; the phone model is off; speed is fixed at 60 km/h at
   12:00, so the night and long-drive factors, parked and indicator rules are not exercised; no enrollment (the
   product asks for one, and then the open-eye reference is clamped around the enrolled value);
3. real driving: 0 hours of normal driving with labels exist. The subjects sit in front of a laptop, by day.

On the held-out subjects all 4 false alarms are one subject's, on one video filmed at 12 FPS, below the 15 FPS the
system commits to. Counting rules fixed before the next scoring: `eval/splits/README.md`. Number of times the held-out
subjects have been read: `eval/splits/uta_rldd_test_reads.tsv` and that README.

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
`dataset_fl3d.md`, `dataset_yawdd.md`, `dataset_sust_ddd.md` were not regenerated then; they were on 08/10/2026
(M70), with today's thresholds: FL3D L3 reached on 77 / 95 (was 75), L1 false alarms 1 (was 2), 2.3 / h (was 4.6),
SUST 8.8 / h (was 8.5), YawDD unchanged.

## 6. Measurability

- Face found on ≥ 99 % of frames at every level (dev). Reliable face below 80 % of frames on 2 of 145 videos:
  F2_S23_0 (77.6 %), F4_S42_10 (73.4 %).
- The eye CNN decided on 0.4 % (`0`) to 9.8 % (`5`) of dev frames; the rest is EAR.
- FPS from 12 to 30 across videos; 13 of 145 are below 15 FPS (dev 5, test 8), outside the working range (section 9); resolutions from 240x426 to 2560x1440, portrait and landscape.

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

## 8. Reading the same numbers three more ways (M69, 08/10/2026)

No threshold changed; replayed from the stored traces with the thresholds of 06/10 (block 5 decided again).

**False alarms by person.** The Poisson interval treats every false alarm as independent. Resampling the 24 subjects
with replacement (10 000 draws, seed 0) instead:

| Awake video, drowsiness branch | False alarms | Poisson (95 %) | By person (95 %) | Subjects with ≥ 1 | Per subject min / median / max |
|---|---:|---:|---:|---:|---:|
| Dev, 3.87 h | 5 | 1.3 (0.42–3.0) | 1.3 (0.00–2.8) | 3 of 24 | 0.0 / 0.0 / 11.7 per h |
| Test, 4.08 h | 4 | 1.0 (0.27–2.5) | 1.0 (0.00–3.0) | 1 of 24 | 0.0 / 0.0 / 24.8 per h |

- All 4 test false alarms are F4_S44's (two L1 `drowsy_score` and two L3 `microsleep`, on his one 10-minute `0` video, filmed at 12 FPS);
  the other 23 subjects have none. So the sample is closer to one subject than to four events, and the by-person
  interval reaches 0 below and 3.0 above (Poisson 2.5). It does not make the PRD target (≤ 1.0 / h) any closer.
- With 0 false alarms the by-person interval is 0–0 whatever the number of subjects: read the Poisson bound there.
- FL3D has no person in its labels and the own recordings are one person, so they cannot be resampled by person.

**One fixed operating point** (`eval/results/uta_rldd_tradeoff.md`; `python tools/uta_rldd.py tradeoff`). At the
current thresholds (`risk.drowsy.l1` 40) on the 24 held-out subjects: **0.98 false alarms / h**, **15 / 24** drowsy
videos with a drowsiness alert, **12 / 24** at L3. Swept on dev only:

| `risk.drowsy.l1` | 30 | 35 | 40 (current) | 45 | 50 | 55 | 60 |
|---|---:|---:|---:|---:|---:|---:|---:|
| False alarms / h (dev) | 1.8 | 1.3 | 1.3 | 1.3 | 0.5 | 0.5 | 0.5 |
| `10` with an alert, of 24 | 17 | 15 | 14 | 14 | 12 | 12 | 12 |
| `10` at L3, of 24 | 12 | 12 | 12 | 12 | 12 | 12 | 12 |

- Only the mild alerts depend on `l1`: the 12 subjects with an L3 do not move, from 30 to 60. Staying at or under
  1.0 / h on dev (point estimate) means `l1` ≥ 50 and 12 subjects with an alert instead of 14: the 2 lost are the
  L1-only ones, as noted in the status.
- The test row at the current `l1` was scored once in M53; it is read again here, not swept.

**What a `drowsy_score` band means** (whole minutes after the 30 s start-up, mean score of the minute; the label covers
the whole video, so a `10` minute can be an awake minute):

| Score band | Dev: `0` / `5` / `10` minutes | Dev `10` against `0` | Test: `0` / `5` / `10` minutes | Test `10` against `0` |
|---|---:|---:|---:|---:|
| 0–20 | 192 / 171 / 115 | 37.5 % | 223 / 151 / 102 | 31.4 % |
| 20–40 | 19 / 45 / 51 | 72.9 % | 5 / 44 / 50 | 90.9 % |
| 40–60 (L1 = 40) | 6 / 2 / 25 | 80.6 % | 3 / 27 / 38 | 92.7 % |
| 60–80 | 1 / 0 / 27 | 96.4 % | 0 / 9 / 30 | 100 % |
| 80–100 | 0 / 0 / 0 | – | 0 / 0 / 7 | 100 % |

- The share of `10` minutes only goes up with the score, on both splits: the score points the right way.
- The sharpest change is between the 0–20 and 20–40 bands (the `0` minutes nearly vanish), not at 40: L1 = 40 sits one
  band above where `10` minutes start to dominate. The extra `5` and `10` minutes in 20–40 are what a lower `l1`
  would alert on, with the false alarms of the first table. Absolute shares mean nothing here (three labels with as
  many videos each, while a driver is awake most of the time).

## 9. Counting the same alerts the way the PRD counts them, and by frame rate (M70, 08/10/2026)

No threshold changed. `python tools/uta_rldd.py report --split dev|test` now prints these tables (section 2 of its
output). Rules: `eval/splits/README.md`. Unit: one alert on a `0` video; Poisson 95 % CI.

| Alerts on `0` videos | Dev: alerts, hours, per hour | Test: alerts, hours, per hour |
|---|---:|---:|
| Drowsiness branch, after the 30 s start-up (the "0.98" row; dev 1.3) | 5, 3.87 h, 1.3 (0.42–3.0) | 4, 4.08 h, 1.0 (0.27–2.5) |
| Drowsiness branch, whole video | 6, 4.07 h, 1.5 (0.54–3.2) | 4, 4.28 h, 0.9 (0.25–2.4) |
| All branches, after the start-up | 9, 3.87 h, 2.3 (1.06–4.4) | 4, 4.08 h, 1.0 (0.27–2.5) |
| **All branches, whole video** (the one to put next to the PRD's ≤ 1.0 / h) | 10, 4.07 h, 2.5 (1.18–4.5) | 5, 4.28 h, 1.2 (0.38–2.7) |

- On the held-out subjects the extra alert is one `off_road` L2 in the first 30 s of F4_S48; on dev the extra ones are
  4 `off_road` L2 (the subject looks at the laptop) and 1 drowsiness alert inside the start-up stretch. Counted this
  way, dev is twice test, mostly `off_road`.
- Neither row comes close to a verdict: the upper bound of the last row is 2.7 / h on test and 4.5 / h on dev.
- Detection counted with the same rule as the false alarms (alerts after the start-up only): see section 5 of
  `python tools/uta_rldd.py report` (`10` videos with an alert, both ways).

By frame rate of the video (the system commits to ≥ 15 FPS; no video is dropped from any number above):

| Split | Frame rate | Videos (subjects) | Awake videos, hours scored | Drowsiness false alarms, per hour (95 %) | All-branch alerts on `0`, whole video | `10` videos with an alert |
|---|---|---:|---:|---:|---:|---:|
| Dev | ≥ 15 FPS | 67 (23) | 23, 3.67 h | 3, 0.8 (0.17–2.4) | 8 | 12 / 22 |
| Dev | < 15 FPS | 5 (2) | 1, 0.20 h | 2, 10.1 (1.23–36.6) | 2 | 2 / 2 |
| Test | ≥ 15 FPS | 65 (22) | 21, 3.51 h | 0, 0.0 (0.00–1.1) | 1 | 14 / 23 |
| Test | < 15 FPS | 8 (4) | 3, 0.57 h | 4, 7.1 (1.92–18.1) | 4 | 1 / 2 |

- 6 of the 9 drowsiness false alarms (dev + test) are on the 4 awake videos below 15 FPS, which hold 0.77 of the 7.95
  awake hours scored (about a tenth). The 6 come from 2 videos (one on each split, 2 and 4); the other 2 awake videos
  below 15 FPS have none, and the awake videos from 15 FPS up have 3 on dev and none on test. **Not shown to be the
  frame rate**: 2 videos, 2 people, different cameras, and a video may have a variable frame rate (not checked). To
  tell, replay the 30 FPS traces with frames thinned to 10 / 12 FPS and compare the alerts (not done).
- The `10` videos below 15 FPS are 4 (3 with an alert); too few to say anything about detection at low frame rate.

## 10. The same tables with the code of 09/10/2026 (M94, after M71-M93)

Between section 9 and this one the decision blocks changed in many places (frame gaps M71, silent states M72, context
M73, alert reminders M74 and M92, droop-then-shut M76, non-finite guards M77, pose baselines M80, nod / yawn M81,
blink rate and smaller findings M90, shares by time M93). `python tools/uta_rldd.py report --split dev` and
`--split test` were run again with `config/thresholds.yaml` of 09/10 (sha256 `73401e6a77ce`, commit `2990b41` plus the
uncommitted M92 and M93). The held-out subjects were read **once** for this (fifth logged read in all:
`eval/splits/uta_rldd_test_reads.tsv`); no threshold was chosen on it. Rules: `eval/splits/README.md`.

| Alerts on `0` videos | Dev: alerts, hours, per hour | Test: alerts, hours, per hour |
|---|---:|---:|
| Drowsiness branch, after the 30 s start-up | 5, 3.87 h, 1.3 (0.42–3.0) | 4, 4.08 h, 1.0 (0.27–2.5) |
| Drowsiness branch, whole video | 6, 4.07 h, 1.5 (0.54–3.2) | 4, 4.28 h, 0.9 (0.25–2.4) |
| All branches, after the start-up | 9, 3.87 h, 2.3 (1.06–4.4) | 4, 4.08 h, 1.0 (0.27–2.5) |
| **All branches, whole video** (the one to put next to the PRD's ≤ 1.0 / h) | 10, 4.07 h, 2.5 (1.18–4.5) | 5, 4.28 h, 1.2 (0.38–2.7) |

| Per subject | Dev | Test |
|---|---:|---:|
| `10` videos with a drowsiness alert / reaching L3 | 14 / 12 of 24 | 15 / 12 of 24 |
| `5` videos with a drowsiness alert / reaching L3 | 5 / 3 of 24 | 12 / 9 of 24 |
| `0` videos with a drowsiness alert | 3 of 24 | 1 of 24 |
| AUC of the mean drowsy_score, `10` against `0` | 0.863 | 0.929 |
| Same subject scores higher on `10` than on `0` | 22 of 24 | 23 of 24 |
| Drowsiness false alarms resampled by person, per hour (95 %) | 1.3 (0.00–2.8) | 1.0 (0.00–3.0) |

- **Every count of section 9 is unchanged**, on both splits: the four ways of counting, the table by frame rate (dev
  3 and 2 false alarms at ≥ 15 / < 15 FPS, test 0 and 4), and the subjects alerted. The four false alarms on test are
  still one subject on one 12 FPS video (F4_S44: L1, L1, L3, L3).
- What moved is the score, not the alerts: AUC on test 0.920 → 0.929 and 23 of 24 subjects (was 22) score higher on
  their `10` video; on dev 0.859 → 0.863.
- Why nothing moved on the alert side although M74 added reminders: on dev the reminders were 2 more drowsiness false
  alarms (5 → 7, 1.29 → 1.81 / h, printed, not in this file), and M92 took the reminder of `drowsy_score` away again.
  `off_road` and `phone` are still reminded; no awake video here holds a look away long enough for one.
- The context factors are off in every number here (noon, no driving behind). On dev, replayed at 02:00 after two hours
  of driving: 5 false alarms and 15 of 24 `10` subjects alerted with the factors capped at 1.2 together (M92); 11 and
  18 with the factors stacking (x 1.44, before).
- The low frame rate study (`fps_low_uta_rldd.md`) was written again the same day: every row from 10 to 15 FPS is
  still inside the run-to-run noise of the others.
- Not written again: section 8's trade-off (`uta_rldd_tradeoff.md`) and section 7 (`personalization_uta_rldd.md`), each
  of which reads the held-out subjects once more. Their numbers are those of 08/10 and 06/10.

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
    python tools/uta_rldd.py tradeoff --out eval/results/uta_rldd_tradeoff.md

Not decided here: `perclos_close_ratio` (P80 no better), `risk.drowsy.l1` (50 halves the dev false alarms again
and loses 2 more drowsy subjects; not scored on test), the nod and yawn weights (rare events at a laptop).
