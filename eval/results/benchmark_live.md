# DriverGuard - the loop of `#/live` in a real browser (M51)

The production build (real MediaPipe, real YOLO, Pyodide) opened in Chromium by `frontend/bench/live.bench.mjs`,
with Chrome's fake camera playing 450 frames of a public YawDD clip (640x480, 30 FPS, a face in every frame). The
numbers are the page's own ("Chi tiết kỹ thuật", `frontend/src/live/perf.ts`), read after the given time. 06/10/2026,
Mac ARM (Apple M5), Chromium of Playwright 1.63, headless. Milliseconds, p50 / p95.

Headless Chromium on a development machine is not the hub and not a phone: these rows compare versions of the code
and show which stage reacts to what. Only numbers were read back; the clip was a temporary copy outside the repo.

## 1. Which delegate for the face model (block 3), before M51's rule

15 s each, page not cross-origin isolated (YOLO on one thread).

| WebGL drawn by | MediaPipe delegate | Face model | Whole frame | FPS shown | Camera frames never processed |
|---|---|---:|---:|---:|---:|
| SwiftShader (software, the headless default) | GPU | 44.8 / 52.1 | 46.8 / 55.1 | 19 | 129 / 429 |
| SwiftShader | CPU | 8.9 / 9.7 | 10.6 / 13.1 | 30 | 2 / 302 |
| Apple M5 (Metal) | GPU | 12.8 / 15.1 | 15.7 / 19.3 | 30 | 3 / 303 |
| Apple M5 (Metal) | CPU | 15.4 / 17.4 | 18.3 / 20.8 | 30 | 6 / 306 |

- On a software rasterizer the "GPU" delegate is 5 times slower than the CPU delegate and the loop falls to about
  20 FPS. M51: the page asks WebGL who draws it and takes the CPU delegate unless it is a real GPU.
- On this real GPU the two are close (the GPU delegate about 2.5 ms faster).
- Handing MediaPipe the video element instead of the canvas changed nothing measurable (real GPU, 12 s each:
  GPU delegate 10.4 / 14.2 with the canvas, 11.1 / 12.9 with the video; CPU delegate 15.2 / 16.2 and 14.8 / 15.1):
  not done.

## 2. Phone detector (block 4): one thread or two

20 s each, software WebGL, face model on the CPU delegate.

| Page | YOLO threads | One inference | Age of the result in use | Whole frame |
|---|---:|---:|---:|---:|
| not cross-origin isolated (before M51) | 1 | 172.1 / 177.7 | 299 / 400 | 10.5 / 12.6 |
| cross-origin isolated (`require-corp` or `credentialless`) | 2 | 90.7 / 105.1 | 230 / 331 | 10.9 / 13.5 |

- `phone.max_result_age_s` is 600 ms: the p95 age moved from 400 to 331 ms.
- The main loop did not slow down with the second YOLO thread on this 10-core machine. Not measured on a 4-core one.

## 3. After M51, served by the deployment's own server (`deploy/railway_app.py`), 30 s each

| WebGL drawn by | Delegate chosen | Start-up (cached) | Capture -> loop | Canvas | Face model | Pixel stats | Python (6-14) | YOLO prep | YOLO run | YOLO result age | Whole frame | Frames never processed |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SwiftShader (software) | CPU | 6.7 s | 0.2 / 16.3 | 0.5 / 0.8 | 8.9 / 10.4 | 0.2 / 0.2 | 0.9 / 1.2 | 1.5 / 1.7 | 90.3 / 108.7 | 229 / 330 | 10.6 / 13.7 | 2 / 302 |
| Apple M5 (Metal) | GPU | 9.1 s | 14.9 / 16.7 | 1.8 / 4.4 | 10.4 / 14.5 | 0.2 / 0.3 | 1.2 / 1.7 | 1.6 / 2.0 | 93.9 / 97.9 | 232 / 332 | 14.6 / 19.9 | 7 / 307 |

Both: 30 FPS, cross-origin isolated, YOLO on 2 threads.

## 4. M67: before and after, same machine, same procedure (08/10/2026)

Apple M5 (4 performance + 6 efficiency cores), 16 GB, macOS 27.0.1, on mains power. Chromium 153.0.8010.12 of
Playwright 1.63.0, headless, a fresh browser profile for every run. The page is the production build served by
`vite preview` with the isolation headers; the camera is Chrome's fake device playing the first 450 frames of a
public YawDD clip (640x480, 30 FPS, a face in every frame) in a loop. "Before" is the code of M51-M56 with only
the counters of this milestone added (the loop itself untouched); "after" is M67. Five runs of 60 s each, the two
builds taken in turn (before, after, before, after ...), in both ways WebGL can be drawn on this machine.
Stages are p50 / p95 over the last 300 frames of a run, then the median of the five runs; the frame counts are
over the whole run, median (lowest-highest).

| | Before, software WebGL | After, software WebGL | Before, real GPU | After, real GPU |
|---|---:|---:|---:|---:|
| Runs of 60 s | 5 | 5 | 5 | 5 |
| Frames processed per second (camera: 30.0) | 29.87 (29.37–29.95) | 29.65 (28.78–30.00) | 29.55 (11.96–29.92) | 29.69 (28.77–29.77) |
| Camera frames never processed, % | 0.44 (0.06–2.11) | 1.00 (0.06–4.00) | 1.00 (0.00–2.17) | 0.94 (0.78–4.11) |
| Whole frame, ms | 10.7 / 13.6 | 11.0 / 13.4 | 14.3 / 19.3 | 12.3 / 17.7 |
| Capture -> loop, ms | 0.2 / 14.3 | 0.2 / 15.7 | 4.8 / 16.8 | 13.3 / 16.0 |
| Canvas (draw + read back), ms | 0.5 / 0.7 | 0.5 / 0.8 | 1.5 / 2.0 | 1.9 / 2.2 |
| Face model, ms | 9.0 / 10.3 | 9.3 / 10.1 | 10.6 / 14.2 | 8.6 / 11.8 |
| Face model p95 / p50 | 1.13 | 1.10 | 1.32 | 1.37 |
| Pixel stats, ms | 0.2 / 0.2 | 0.2 / 0.2 | 0.2 / 0.2 | 0.3 / 0.3 |
| Python (6-14), ms | 1.0 / 1.3 | 1.0 / 1.3 | 1.1 / 1.5 | 1.3 / 1.7 |
| YOLO preparation, ms | 1.5 / 1.7 | 1.5 / 1.8 | 1.7 / 1.9 | 2.1 / 2.4 |
| YOLO, one run, ms | 90.7 / 93.6 | 94.4 / 97.1 | 94.5 / 97.9 | 17.0 / 20.1 |
| YOLO runs per second | 4.55 | 5.00 | 4.55 | 10.00 |
| Age of the YOLO result in use, ms | 229.9 / 328.8 | 199.4 / 273.6 | 232.6 / 332.8 | 67.2 / 130.9 |
| ... largest | 340 | 304 | 341 | 141 |
| CPU of the page, % of one core | 125 | 137 | 109 | 32 |
| CPU of the GPU process, % | 2 | 2 | 15 | 23 |
| Start to first frame, s (empty cache) | 2.66 (2.39–3.59) | 2.08 (2.04–2.45) | 2.62 (2.48–3.15) | 2.21 (2.16–2.80) |
| ... Python ready at, s | 2.29 | 1.81 | 2.15 | 1.80 |
| ... phone model ready at, s | 2.49 | 2.18 | 2.35 | 2.32 |

- **The loop was not the bottleneck and still is not:** a frame keeps the main thread busy 11-14 ms of the 33 ms
  between camera frames, before and after. The frame rate is the camera's.
- **Age of the YOLO result in use** is what moved: p95 329 -> 274 ms without a GPU (same model on wasm, now run
  exactly 5 times a second and fed before MediaPipe), 333 -> 131 ms with one (WebGPU, 17 ms a run, 10 times a
  second). The proposed 250 ms is met with a real GPU and missed by 24 ms without one; see the rejected step below.
- **CPU:** with a real GPU the page's process went from 109 % to 32 % of one core (the two wasm threads are
  gone), the GPU process from 15 % to 23 %. Without a GPU, 125 % -> 137 % (5.0 runs a second instead of 4.55).
- **Camera frames never processed: no difference that these runs can show.** 0.06-2.1 % before and 0.06-4.0 %
  after without a GPU, 0.0-2.2 % and 0.8-4.1 % with one; the spread between two runs of the same build is larger
  than any difference between the builds. Section 5 has ten minutes of each. Profiled from outside the page
  (60 s, unmodified build): in 20 of 21 such frames the main thread had been idle for 35-40 ms, no task longer
  than 50 ms ran after the first frame, the handlers of timers and of YOLO results took 0.2-0.5 ms.
  `requestVideoFrameCallback` only fires when the browser draws, and a camera frame that arrives across that
  rhythm is replaced before its turn. The same rhythm decides "capture -> loop": in some runs every frame waits
  about 15 ms for the next draw (p50 13 ms in the "after, real GPU" column, 0.2 ms in others of the same build).
- **Face model:** p95 within 1.1-1.4 times p50 in every column. The 44 ms tail and the 24 % of frames lost that
  M50 reported were the GPU delegate on a software rasterizer, removed by M51.
- One "before, real GPU" run only got 12.0 frames a second from the fake camera itself (none was skipped by the
  loop); it is the low end of that cell.

### The steps, one at a time (60 s runs, median of 2-3)

| Step | Kept | YOLO runs / s | One run, ms | Age in use p50 / p95, ms | CPU of the page, % of one core |
|---|:---:|---:|---:|---:|---:|
| Before (software WebGL / real GPU) | | 4.53 / 4.55 | 90.9 / 94.1 | 233 / 333 · 232 / 333 | 125 / 111 |
| 1. Frame nearest the due time, fed before MediaPipe | yes | 5.00 / 5.00 | 91.8 / 93.3 | 197 / 267 · 199 / 267 | 136 / 117 |
| 2. wasm at 10 runs / s | **no** | 7.9-8.7 reached | 97.3 | 166 / 230-233 | 211-216 |
| 3. WebGPU where a real GPU adapter exists, 10 runs / s there | yes | – / 10.00 | – / 16.2 | – · 67 / 101 | – / 32 |

- Step 2 was dropped: twice the CPU of the page for 37 ms of p95 age, on exactly the machines that have no GPU.
  The page therefore keeps `phone.target_fps` on wasm and uses `phone.web_gpu_target_fps` only on WebGPU.
- Step 3, age p95: 101 ms in those runs, 101-134 ms in the five of the table above, following "capture -> loop".

### YOLO alone in a worker (40 runs each, random input, Chromium on the same machine)

| Provider | Input | Threads | One run p50, ms | Session + first run, ms |
|---|---:|---:|---:|---:|
| wasm | 640 | 1 / 2 / 3 / 4 / 6 | 168.1 / 87.8 / 61.2 / 49.9 / 66.5 | 108 + 103 (2 threads) |
| wasm | 480 / 416 / 320 | 2 | 51.0 / 38.3 / 23.7 | |
| WebGPU (Metal) | 640 / 416 | – | 11.2 / 6.4 | 417 + 492 |

- Headless Chromium without the GPU flags has no WebGPU adapter: the page stays on wasm there.
- More than 4 threads is slower on this machine (4 fast cores). `phone.num_threads` stayed at 2: it is shared
  with the device and no 4-core machine was measured.
- The smaller inputs are re-exports of the same pretrained weights and are not in use: what they cost in
  detection is in [`phone_web_3mdad.md`](phone_web_3mdad.md).

### The same answers on WebGPU and on wasm

200 frames of 3MDAD (68 with a phone box at 0.35 or more, 39 with their best score between 0.25 and 0.45), the
same input through both providers: the phone score differs by at most 4.7e-6 (median 8.6e-7), box coordinates by
at most 7.3e-4 px, and no box crosses the configured score one way only (0 of 356). A build whose 40th WebGPU run
was made to fail went on with a wasm session on 2 threads at 5 runs a second.

### Start-up (from pressing "start" to the first frame through the whole loop, median of 5; ms)

| | Camera on | Python ready | Face model ready | Phone model ready | First frame |
|---|---:|---:|---:|---:|---:|
| Empty cache, software WebGL: before | 96 | 2285 | 2367 | 2488 | 2660 (2386-3594) |
| Empty cache, software WebGL: after | 93 | 1815 | 1897 | 2183 | 2076 (2035-2450) |
| Empty cache, real GPU: before | 93 | 2148 | 2230 | 2349 | 2619 (2480-3148) |
| Empty cache, real GPU: after | 95 | 1801 | 1880 | 2323 | 2212 (2157-2804) |
| Warm cache (kept browser profile), software WebGL: before | 567 | 1103 | 1165 | 1229 | 1356 (1352-1359) |
| Warm cache, software WebGL: after | 649 | 1080 | 1142 | 1339 | 1292 (1286-1309) |
| Warm cache, real GPU: before | 564 | 1097 | 1163 | 1224 | 1442 (1437-1461) |
| Warm cache, real GPU: after | 651 | 1086 | 1151 | 1532 | 1399 (1390-1435) |

- **Empty cache: 0.4-0.6 s shorter** (2.66 -> 2.08 s and 2.62 -> 2.21 s). Pyodide's packages (numpy is 3 MB) used to
  be downloaded only after the runtime had started; they now come beside it. This part is the network's: Pyodide
  and MediaPipe come from a CDN, and the runs of one build differ by up to a second.
- **Warm cache: 0.04-0.06 s shorter** (1.36 -> 1.29 s and 1.44 -> 1.40 s), the time the loop used to wait for the
  phone model. What is left is Python starting on the main thread: about 0.46 s for the runtime and 0.40 s for
  importing numpy and the agent (two long tasks seen from outside the page), then the face model.
- The phone model is ready after the first frame now: 0.05 s later without a GPU, 0.13 s later with one (a WebGPU
  session takes 0.4 s to build and 0.5 s to warm up, against 0.1 + 0.1 s on wasm). Frames until then have no phone
  answer.
- The 11 s of M50 and the 6.7-9.1 s of section 3 did not reproduce: 2.4-3.6 s on this network with an empty cache.
- **Tried, not kept:** opening the connection to the CDN when `#/live` is shown, before the driver presses start.
  With 3 s spent on the consent screen first (empty cache, software WebGL, 5 runs): 2.03 s with it against 2.08 s
  without (and 2.35 s against 2.66 s for the old build, which never had it): nothing these runs can tell from the
  network's own spread.

## 5. M67: ten minutes each (`bench/live.bench.mjs --duration 10m`)

Same machine, clip and builds as section 4, one run at a time. Judged like `tools/benchmark.py --duration`: at
least `eval.soak_min_fps` (15) in every minute, and the page's process growing by less than
`eval.soak_rss_growth_mb_per_h` (20) after the first minute.

| Run | Started | Frames / s, whole run | Lowest minute | Camera frames never processed | YOLO runs / s | Age in use p95 (last 10 s) | CPU of the page | Page memory start -> end (MB) | FPS >= 15 every minute | Memory |
|---|---|---:|---:|---:|---:|---:|---:|---:|:---:|:---:|
| Before, software WebGL | 00:52 | 29.88 | 29.2 | 72 / 17999 (0.40 %) | 4.56 | 333 ms | 129 % | 746 -> 887 | PASS | PASS |
| **After, software WebGL, first run** | 01:02 | 9.45 | **0.0** | 19 / 5688 | 1.58 | 267 ms | 48 % | 788 -> 311 | **FAIL** | PASS |
| Before, real GPU | 01:12 | 29.59 | 28.4 | 245 / 18000 (1.36 %) | 4.56 | 333 ms | 108 % | 725 -> 476 | PASS | PASS |
| **After, real GPU, first run** | 01:22 | 7.01 | **0.0** | 101 / 4305 | 2.39 | 130 ms | 10 % | 1063 -> 425 | **FAIL** | PASS |
| After, software WebGL, repeated | 01:40 | 29.70 | 28.7 | 180 / 17998 (1.00 %) | 5.00 | 267 ms | 136 % | 782 -> 951 | PASS | PASS |
| After, real GPU, repeated | 01:51 | 29.68 | 29.2 | 192 / 18000 (1.07 %) | 10.00 | 101 ms | – | 1078 -> 517 | PASS | PASS |

**The two first runs of the new build failed, and why is not known.**

- What happened: the loop stopped getting frames. Without a GPU: full speed for 75 s, nothing for 20 s, full
  speed for 50 s, nothing for 70 s, full speed for 80 s, then nothing for the last 5 minutes. With a GPU: full
  speed for 145 s, then nothing until the end. While stopped the page's process used 3-4 % of a core; no error,
  no crash, the page still answered. The counter of frames the camera delivered stopped with it, since it is
  read in the same callback.
- What speaks for the machine and not the code: `requestVideoFrameCallback` not firing with an idle main thread
  is the browser not presenting video frames, and nothing in the page's JavaScript runs in between; the loop
  re-registers the callback unconditionally; one run resumed twice by itself. The two repeated runs passed, and so
  did both builds in both configurations run **at the same time** for 15 minutes with event logging on the camera
  track, the video element and the page's visibility (lowest minute 26.8-28.2 FPS for all four, no event). The
  developer left the machine at about 01:02 and its screen was locked when this was looked at.
- What speaks against: it hit the new build 2 times out of 2 and the old one 0 out of 2, and it was not
  reproduced on purpose (turning the display off for 40 s under both builds did not stop either).
- So: **the new build passed this gate in 2 runs of 10 minutes and failed it in 2**, with a cause that points
  outside the page but is not established. It is the same dependence on the browser's drawing rhythm as the
  frames never processed in section 4; taking frames from the camera track directly would remove it.
- Memory: every slope is negative (the OS trims the process during the run: -1076 to -3597 MB / h), so the
  criterion passes without saying much; ten minutes cannot show a slow leak. The device's own long runs read the
  same way (`benchmark_simulated.md`).
- Frames never processed over ten minutes: 0.40 % and 1.36 % before, 1.00 % and 1.07 % after.


## How to run it again

```
cd frontend && npx vite build && npx vite preview --port 5191 &
node bench/live.bench.mjs --url http://localhost:5191 --seconds 30 --camera /path/to/clip.mjpeg
node bench/live.bench.mjs ... --delegate CPU                                              # force a delegate
node bench/live.bench.mjs ... --chrome-args "--use-angle=metal --enable-gpu --ignore-gpu-blocklist"   # a real GPU on macOS
node bench/live.bench.mjs ... --seconds 60 --json run.json                                    # whole-run counters (M67)
node bench/live.bench.mjs ... --duration 10m                                               # long run with a verdict
node bench/live.bench.mjs ... --seconds 3 --profile /tmp/dg-profile                        # twice: the second start is a warm cache
node bench/live.bench.mjs ... --yolo wasm                                                  # force the phone detector's provider
```

`--camera` takes an `.mjpeg` (JPEG frames back to back) or `.y4m` file; without it Chrome's test pattern, which has
no face. On another machine or a phone, open `#/live` there and read "Chi tiết kỹ thuật" instead.
