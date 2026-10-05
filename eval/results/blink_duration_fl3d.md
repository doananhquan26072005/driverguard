# Blink duration vs the driver's own blinks: offline prototype on FL3D (M35)

Traces only (blocks 5, 7-12 replayed with config/thresholds.yaml; no video, no model): 44 videos, 47.2 min, 25 FPS (40 ms per frame). The engine is not changed by this report.

## 1. How many blinks can be measured

- Block 7 timed **482 blinks** (10.2 per minute). Per video: median 7, min 0, max 42.
- Duration (aperture below 0.8 and back): median 304 ms, p5-p95 114-1203 ms. Reopening: median 186 ms.
- A `duration_ratio` like `reopen_ratio` needs the first 20 blinks as the driver's own baseline, then 5 more to compare: **5 of 44 videos** have that many. The clips are too short for a ratio against the start of the trip.

## 2. Drowsy against alert

FL3D has no drowsy-stretch label (frames are alert / microsleep / yawning). Stand-ins: videos with a labelled microsleep (19) against videos without (25); and, inside the microsleep videos, blinks within 10 s of a microsleep against the rest. Closures longer than 1.5 s are not blinks and are left out on both sides.

| Timing | Blinks, microsleep videos | Median ms | Blinks, other videos | Median ms | Ratio | AUC |
|---|---:|---:|---:|---:|---:|---:|
| Block 7 (EAR) | 342 | 310 | 140 | 280 | 1.11 | 0.54 |
| Offline, EAR | 885 | 274 | 293 | 217 | 1.26 | 0.60 |
| Offline, eyeBlink | 811 | 205 | 290 | 177 | 1.16 | 0.56 |

AUC: chance that a blink from a microsleep video is longer than one from another video (0.5 = no difference). The videos are of different people, so this also carries person-to-person differences.

| Timing | Blinks near a microsleep | Median ms | Other blinks, same videos | Median ms | Ratio | AUC | Videos with >= 5 on both sides | Median per-video ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Block 7 (EAR) | 300 | 311 | 42 | 296 | 1.05 | 0.54 | 5 | 1.00 |
| Offline, EAR | 811 | 275 | 74 | 228 | 1.21 | 0.56 | 7 | 1.07 |
| Offline, eyeBlink | 758 | 208 | 53 | 200 | 1.04 | 0.51 | 5 | 0.96 |

## 3. EAR against eyeBlink

Same offline timer on both signals (dip below 0.8 reaching 0.5, back within 1.5 s): 1178 blinks on EAR, 1101 on eyeBlink (41 videos have a closure to scale eyeBlink with). Median duration 264 ms on EAR, 199 ms on eyeBlink. Rank correlation of the per-video medians: 0.72 over 38 videos with >= 5 blinks on both.

The offline timer finds 2.4 times as many blinks on EAR as block 7 times (1178 against 482). Block 7 only times a dip that its closure rule called a blink; why it leaves out more than half was not looked into here.

## 4. Duration against reopening time

Per blink (block 7, 482 blinks): Spearman rho = **0.92**. Duration and reopening time rank the blinks almost the same way: a longer blink is mostly a slower reopening.

## 5. Verdict

Rules: add `duration_ratio` only if it separates (AUC >= 0.65) **and** adds to `reopen_ratio` (|rho| <= 0.8). The two cut-offs were picked after a first look at the numbers, so they are not pre-registered; what matters is how far the result is from them.

- Separation: best AUC of block 7's timing 0.54 -> **not met**.
- Adds to `reopen_ratio`: rho 0.92 -> **not met**.

**Do not add `duration_ratio` to the engine on this evidence.**

## Limits

- NITYMED drowsiness is acted, at night, in clips of 15 s to 2.5 min: a real slow drift over a drive is not in it.
- One frame is 40 ms; the 30 ms group difference of Häkkänen 1999 (EOG) is below it. Only medians over many blinks mean anything.
- "Near a microsleep" is a stand-in for drowsy, chosen here; UTA-RLDD (same person at KSS levels) is the dataset that can really answer question 1.
- The eyeBlink scale is each video's own (median = open, 99.5th percentile = closed), not the engine's.
