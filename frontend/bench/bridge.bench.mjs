// Per-frame cost of the in-browser agent's Python (blocks 6-14, edge_agent/web/bridge.py) in Pyodide,
// run by tools/bench_web.py:   node bench/bridge.bench.mjs <edge_agent.zip> <frames.json>
// The same call the page makes for every camera frame (agent.frame + JSON.parse), on landmark
// numbers only: no camera, no image. Node runs the same V8 as Chrome / WebView, but this is not a
// browser and not the hub. Prints one JSON document on the last line.
import fs from "node:fs";
import { loadPyodide } from "pyodide";

const [zipPath, framesPath] = process.argv.slice(2);
const input = JSON.parse(fs.readFileSync(framesPath, "utf8"));
const W = input.width;
const H = input.height;
const frames = input.frames.map((f) => ({ points: Float32Array.from(f.points), blink: f.blink, brow: [f.brow] }));

const t0 = performance.now();
const py = await loadPyodide();
await py.loadPackage(["numpy", "pyyaml", "sqlite3"], { messageCallback: () => {} }); // as agent.ts
const missing = ["numpy", "pyyaml", "sqlite3"].filter((name) => !py.loadedPackages[name]);
if (missing.length) {
  // loadPackage only logs a failed download. The wheels are cached next to the runtime once fetched.
  console.error(`Pyodide packages not loaded: ${missing.join(", ")} (download failed?). Retry, or put the wheels of Pyodide ${py.version} in frontend/node_modules/pyodide/.`);
  process.exit(2);
}
const zip = fs.readFileSync(zipPath);
py.unpackArchive(zip.buffer.slice(zip.byteOffset, zip.byteOffset + zip.byteLength), "zip", { extractDir: "/home/pyodide/dg" });
py.runPython('import sys; sys.path.insert(0, "/home/pyodide/dg")');
const bridge = py.pyimport("edge_agent.web.bridge");
const agent = bridge.WebAgent.callKwargs("bench", "trip-bench", { scenario: input.scenario });
const startupMs = performance.now() - t0;

const ms = [];
frames.forEach((f, i) => {
  const t = 100 + i / input.fps;
  const s = performance.now();
  JSON.parse(agent.frame(t, i, W, H, f.points, 1, f.blink, 30.0, 110.0, f.brow, 110.0, 40.0, 150.0));
  ms.push(performance.now() - s);
});
const timed = ms.slice(input.warmup_frames).sort((a, b) => a - b);
const at = (p) => timed[Math.min(timed.length - 1, Math.floor((p / 100) * timed.length))];

// Where the time goes inside Python: a second trip under cProfile (slower, so only shares are kept).
py.runPython(`
import cProfile, json, pstats
import numpy as np
from edge_agent.web.bridge import WebAgent

def profile(doc):
    doc = json.loads(doc)
    frames = [(np.asarray(f["points"], np.float32), f["blink"], [f["brow"]]) for f in doc["frames"]]
    agent = WebAgent("bench", "trip-profile", scenario=doc["scenario"])
    warm = doc["warmup_frames"]
    pr = cProfile.Profile()
    for i, (pts, blink, brow) in enumerate(frames):
        if i == warm:
            pr.enable()
        agent.frame(100 + i / doc["fps"], i, doc["width"], doc["height"], pts, 1, blink, 30.0, 110.0, brow, 110.0, 40.0, 150.0)
    pr.disable()
    out, calls = {}, 0
    for (path, _line, name), (_cc, nc, _tt, ct, _callers) in pstats.Stats(pr).stats.items():
        if name == "_frame" and path.endswith("web/bridge.py"):
            out["frame"] = ct
        elif name == "solve_pnp":
            out["head_pose_solve_pnp"] = ct
        elif name == "__call__" and path.endswith("perception/features.py"):
            out["features"] = ct
        elif name == "step" and path.endswith("decision/pipeline.py"):
            out["decision_pipeline"] = ct
        elif name == "step" and path.endswith("edge_agent/runtime.py"):
            out["runtime_step"] = ct
        elif name == "dumps":
            out["json_dumps"] = out.get("json_dumps", 0.0) + ct
        elif name in ("_project", "_jacobian") and path.endswith("perception/geometry.py"):
            calls += nc  # every pass over the model points
    total = out.get("frame") or 1.0
    n = len(frames) - warm
    return json.dumps({"shares": {k: v / total for k, v in out.items()}, "project_calls_per_frame": calls / n})
`);
const profile = JSON.parse(py.globals.get("profile")(fs.readFileSync(framesPath, "utf8")));

console.log(
  JSON.stringify({
    pyodide: py.version,
    node: process.version,
    startup_ms: startupMs,
    frames: timed.length,
    mean_ms: timed.reduce((a, b) => a + b, 0) / timed.length,
    p50_ms: at(50),
    p95_ms: at(95),
    p99_ms: at(99),
    max_ms: timed.at(-1),
    ...profile,
  }),
);
