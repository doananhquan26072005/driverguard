# DriverGuard - the phone branch against how and when YOLO runs (3MDAD)

`tools/phone_study.py`. 3MDAD day set, face camera (`RGB2`): 50 drivers, 111017 frames, 1.03 h at an assumed 30 FPS. YOLO ran once on every frame (the plain 640-wide frame block 4 gets); every schedule below is then played on those boxes: which frame the detector would have been given, when its answer would have been back, what each frame would have seen. Blocks 7-12 are replayed on the trace of `tools/gaze_study.py` with that phone flag. Numbers only, no image kept.

Positives: the 4 phone actions (message right / left hand, call right / left hand), one sequence per driver and action. "Taking a picture" (AC9) is done with a phone in the hand: its alerts are counted on neither side. Negatives: the other 11 actions. An alert up to 1 s after a sequence still belongs to it. Thresholds as configured: score >= 0.35, driver zone, `phone_ratio` 0.6 over 2 s, answers older than 600 ms unknown.

Acted sequences of 3-5 s at one camera position: a `phone` alert needs about 1.7 s, so the recall here is far below a real call. Read the rows against each other.

Every row is played 6 times, the detector starting on frame 0 .. 5, and summed: which frames it happens to get moves a borderline sequence across the alert rule, and one start alone cannot tell that from an effect of the schedule. The starts share the same video, so the summed counts are not independent samples: the per-hour interval is the one of the summed count over the summed hours, an optimistic one.

## 1. Same model (640), different schedules

| Schedule | Runs / s asked | Answer back after (ms) | Age in use p50 / p95 (ms) | Phone sequences with a `phone` alert (recall), all starts | ... per start, of 200 | Precision of the alerts | False `phone` alerts (in the 11 other actions), all starts | ... per start | ... per hour (95 % CI) | `phone` alerts while taking a picture | Sequence start to alert, median / p95 (s) | Frames seeing a phone, inside phone sequences | ... outside | Frames without an answer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| page before M67: wasm, 2 threads | 5 | 105 | 233 / 333 | 134 / 1200 (11.2 %) | 21–23 | 100.0% | 0 | 0–0 | 0.0 (0.0–0.9) | 2 | 2.47 / 4.40 | 18312 / 165342 (11.1 %) | 5139 / 455148 (1.1 %) | 0.3 % |
| page after M67, no GPU: wasm, 2 threads | 5 | 95 | 167 / 267 | 131 / 1200 (10.9 %) | 20–23 | 99.2% | 1 | 0–1 | 0.2 (0.0–1.3) | 2 | 2.47 / 4.97 | 18031 / 165342 (10.9 %) | 4944 / 455448 (1.1 %) | 0.2 % |
| page after M67, real GPU: WebGPU | 10 | 20 | 67 / 100 | 130 / 1200 (10.8 %) | 21–22 | 98.5% | 2 | 0–1 | 0.5 (0.1–1.7) | 0 | 2.33 / 4.87 | 18052 / 165342 (10.9 %) | 4854 / 456048 (1.1 %) | 0.2 % |
| tried, not kept: wasm at 10 / s | 10 | 100 | 133 / 200 | 138 / 1200 (11.5 %) | 23–23 | 100.0% | 0 | 0–0 | 0.0 (0.0–0.9) | 0 | 2.47 / 5.20 | 18096 / 165342 (10.9 %) | 4860 / 455448 (1.1 %) | 0.2 % |
| for reference: every frame, at once | 1000 | 0 | 0 / 0 | 138 / 1200 (11.5 %) | 23–23 | 100.0% | 0 | 0–0 | 0.0 (0.0–0.9) | 0 | 2.30 / 4.37 | 18078 / 165342 (10.9 %) | 4806 / 456348 (1.1 %) | 0.1 % |

Per phone action (sequences with a `phone` alert):

| Schedule | AC5 writing a message, right hand | AC6 writing a message, left hand | AC7 phone call, right hand | AC8 phone call, left hand |
|---|---:|---:|---:|---:|
| page before M67: wasm, 2 threads | 118 / 300 | 4 / 300 | 12 / 300 | 0 / 300 |
| page after M67, no GPU: wasm, 2 threads | 114 / 300 | 6 / 300 | 11 / 300 | 0 / 300 |
| page after M67, real GPU: WebGPU | 114 / 300 | 4 / 300 | 12 / 300 | 0 / 300 |
| tried, not kept: wasm at 10 / s | 120 / 300 | 6 / 300 | 12 / 300 | 0 / 300 |
| for reference: every frame, at once | 126 / 300 | 0 / 300 | 12 / 300 | 0 / 300 |

### How much the choice of frames alone moves the result

Every k-th frame, the answer back 3 frames later (100 ms), from each of the k possible first frames. No rule of the page is involved: the spread over the offsets is sampling luck, and a difference between two rows of the table above that is smaller than it is not an effect of the schedule.

| Every k-th frame | Runs / s | Phone sequences with a `phone` alert, per offset (of 200) | Mean | False `phone` alerts, per offset | Plays with a false alert |
|---:|---:|---|---:|---|---:|
| 3 | 10.0 | 23, 22, 21 | 22.0 | 1, 0, 0 | 1 / 3 |
| 6 | 5.0 | 22, 22, 23, 20, 22, 22 | 21.8 | 0, 0, 0, 1, 0, 0 | 1 / 6 |
| 7 | 4.3 | 23, 20, 22, 25, 21, 22, 18 | 21.6 | 0, 1, 1, 0, 0, 0, 1 | 3 / 7 |

## 2. Smaller input, same pretrained weights re-exported (not in use)

Schedule of every row: 5 runs / s, answer back after 95 ms (the same for every size, so only what the model sees differs).

| Input | Runs / s asked | Answer back after (ms) | Age in use p50 / p95 (ms) | Phone sequences with a `phone` alert (recall), all starts | ... per start, of 200 | Precision of the alerts | False `phone` alerts (in the 11 other actions), all starts | ... per start | ... per hour (95 % CI) | `phone` alerts while taking a picture | Sequence start to alert, median / p95 (s) | Frames seeing a phone, inside phone sequences | ... outside | Frames without an answer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 640 | 5 | 95 | 167 / 267 | 131 / 1200 (10.9 %) | 20–23 | 99.2% | 1 | 0–1 | 0.2 (0.0–1.3) | 2 | 2.47 / 4.97 | 18031 / 165342 (10.9 %) | 4944 / 455448 (1.1 %) | 0.2 % |
| 480 | 5 | 95 | 167 / 267 | 130 / 1200 (10.8 %) | 19–24 | 100.0% | 0 | 0–0 | 0.0 (0.0–0.9) | 11 | 2.33 / 4.12 | 19352 / 165342 (11.7 %) | 3687 / 455448 (0.8 %) | 0.2 % |
| 416 | 5 | 95 | 167 / 267 | 132 / 1200 (11.0 %) | 19–26 | 100.0% | 0 | 0–0 | 0.0 (0.0–0.9) | 12 | 2.33 / 4.31 | 18525 / 165342 (11.2 %) | 2601 / 455448 (0.6 %) | 0.2 % |
| 320 | 5 | 95 | 167 / 267 | 87 / 1200 (7.2 %) | 12–17 | 100.0% | 0 | 0–0 | 0.0 (0.0–0.9) | 16 | 2.23 / 3.43 | 12845 / 165342 (7.8 %) | 993 / 455448 (0.2 %) | 0.2 % |

The model alone, every frame its own answer (share of the frames of an action with a phone box at the configured score: anywhere in the image / in the driver zone):

| Action | Frames | 640: anywhere / in zone | 480: anywhere / in zone | 416: anywhere / in zone | 320: anywhere / in zone |
|---|---:|---:|---:|---:|---:|
| AC1 safe driving | 6761 | 0.2 % / 0.1 % | 0.3 % / 0.1 % | 0.2 % / 0.0 % | 0.0 % / 0.0 % |
| AC2 hair / makeup | 6453 | 0.3 % / 0.2 % | 0.4 % / 0.2 % | 0.4 % / 0.2 % | 0.1 % / 0.1 % |
| AC3 adjusting the radio | 6534 | 0.1 % / 0.1 % | 0.1 % / 0.1 % | 0.1 % / 0.1 % | 0.0 % / 0.0 % |
| AC4 operating the GPS | 7657 | 0.3 % / 0.3 % | 0.5 % / 0.2 % | 0.2 % / 0.1 % | 0.2 % / 0.0 % |
| AC5 writing a message, right hand **(phone)** | 6337 | 36.3 % / 35.6 % | 41.9 % / 40.8 % | 41.1 % / 40.2 % | 31.2 % / 30.5 % |
| AC6 writing a message, left hand **(phone)** | 6360 | 0.4 % / 0.3 % | 1.5 % / 0.3 % | 0.8 % / 0.3 % | 0.1 % / 0.1 % |
| AC7 phone call, right hand **(phone)** | 7373 | 7.5 % / 7.4 % | 6.8 % / 6.6 % | 6.0 % / 5.9 % | 2.2 % / 2.1 % |
| AC8 phone call, left hand **(phone)** | 7487 | 2.8 % / 2.6 % | 2.0 % / 1.7 % | 1.5 % / 1.2 % | 0.8 % / 0.7 % |
| AC9 taking a picture (phone in the hand) | 7277 | 14.5 % / 13.2 % | 17.9 % / 15.8 % | 18.1 % / 16.1 % | 15.0 % / 13.7 % |
| AC10 talking to the passenger | 8379 | 1.9 % / 1.7 % | 1.2 % / 0.7 % | 1.3 % / 0.9 % | 0.7 % / 0.3 % |
| AC11 singing / dancing | 7243 | 1.1 % / 0.8 % | 1.0 % / 0.5 % | 0.9 % / 0.4 % | 0.4 % / 0.3 % |
| AC12 fatigue | 6834 | 0.5 % / 0.5 % | 0.3 % / 0.2 % | 0.2 % / 0.1 % | 0.0 % / 0.0 % |
| AC13 drinking, right hand | 6387 | 3.4 % / 3.4 % | 2.4 % / 2.3 % | 1.5 % / 1.5 % | 0.4 % / 0.4 % |
| AC14 drinking, left hand | 6396 | 0.8 % / 0.7 % | 0.6 % / 0.5 % | 0.3 % / 0.2 % | 0.0 % / 0.0 % |
| AC15 reaching behind | 5801 | 0.3 % / 0.3 % | 0.4 % / 0.3 % | 0.3 % / 0.2 % | 0.3 % / 0.2 % |
| AC16 smoking | 7738 | 3.3 % / 3.1 % | 3.5 % / 3.0 % | 2.3 % / 2.0 % | 0.6 % / 0.5 % |
