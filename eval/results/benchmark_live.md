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

## How to run it again

```
cd frontend && npx vite build && npx vite preview --port 5191 &
node bench/live.bench.mjs --url http://localhost:5191 --seconds 30 --camera /path/to/clip.mjpeg
node bench/live.bench.mjs ... --delegate CPU                                              # force a delegate
node bench/live.bench.mjs ... --chrome-args "--use-angle=metal --enable-gpu --ignore-gpu-blocklist"   # a real GPU on macOS
```

`--camera` takes an `.mjpeg` (JPEG frames back to back) or `.y4m` file; without it Chrome's test pattern, which has
no face. On another machine or a phone, open `#/live` there and read "Chi tiết kỹ thuật" instead.
