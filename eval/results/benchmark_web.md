# DriverGuard - speed of the in-browser agent's Python (blocks 6-14)

One row per run of `tools/bench_web.py`: the page's per-frame call `WebAgent.frame()` + JSON on the same landmark numbers, in CPython with OpenCV (the device's case) and in Pyodide under Node (the code of `#/live` and the APK). Node is not a browser and these machines are not the hub: the rows compare versions of the code. Canvas, MediaPipe and YOLO are not in these numbers.

| Run | Date | Machine | Input | Device: p50 / p95 ms | Pyodide: p50 / p95 / max ms | Pyodide / device | Head pose (solve_pnp) share | Projections / frame | Pyodide start (ms) |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| trước M49 (mặt tổng hợp) | 06/10/2026 | arm64, Darwin | synthetic moving face, 60 s at 30 FPS | 0.17 / 0.24 | 1.47 / 1.94 / 4.1 | 8.7x | 70 % | 75.0 | 1076 |
| trước M49 (clip YawDD) | 06/10/2026 | arm64, Darwin | 1-FemaleNoGlasses.avi, 1800 frames with a face | 0.18 / 0.25 | 1.97 / 2.70 / 7.2 | 10.8x | 77 % | 101.3 | 1446 |
| sau M49 (mặt tổng hợp) | 06/10/2026 | arm64, Darwin | synthetic moving face, 60 s at 30 FPS | 0.14 / 0.21 | 0.56 / 0.72 / 2.0 | 3.9x | 50 % | 9.1 | 1139 |
| sau M49 (clip YawDD) | 06/10/2026 | arm64, Darwin | 1-FemaleNoGlasses.avi, 1800 frames with a face | 0.15 / 0.21 | 0.61 / 0.88 / 11.0 | 4.2x | 52 % | 9.8 | 1327 |

- Share: cumulative time of `geometry.solve_pnp` over that of `bridge._frame`, under cProfile in Pyodide. Projections: passes over the model points per frame (`geometry._project` and `_jacobian`).
- Pyodide start: runtime + numpy + pyyaml + sqlite3 + `WebAgent()` from the local disk, without downloads.
- Software of the last run: Python 3.12.14; numpy 1.26.4; Pyodide 0.29.3; Node v26.9.0
