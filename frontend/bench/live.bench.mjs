// The loop of #/live in a real browser: opens a served build in Chromium with Chrome's fake camera
// and reads the page's own timings ("Chi tiết kỹ thuật", src/live/perf.ts) while it runs.
//
//   npx vite build && npx vite preview --port 5191 &
//   node bench/live.bench.mjs --url http://localhost:5191 --seconds 30 [--camera clip.mjpeg] [--headed]
//   node bench/live.bench.mjs ... --duration 10m --json soak.json     # long run, judged like tools/benchmark.py --duration
//   node bench/live.bench.mjs ... --seconds 5 --profile /tmp/dg-profile   # run twice: the second start-up has a warm cache
//   node bench/live.bench.mjs ... --delegate CPU --yolo wasm            # force MediaPipe's delegate / the phone detector's provider
//   node bench/live.bench.mjs ... --think-s 3                           # wait on the consent screen first, as a driver reading it does
//
// --camera: an .mjpeg / .y4m file Chrome plays as the camera (a public dataset clip, so a face is in
// view); without it Chrome's test pattern (no face). The page is the production build: real
// MediaPipe, real YOLO, Pyodide. Numbers only are read back; nothing is recorded.
// Every --sample-s seconds (10) the page's counters since the start are read (frames processed, camera
// frames never processed, YOLO runs), with the memory and CPU time of the browser's processes. A run of
// two minutes or more gets a verdict against eval.soak_min_fps (every minute) and
// eval.soak_rss_growth_mb_per_h (renderer process, after the first minute) of config/thresholds.yaml.
// The page also says how often its loop watch had to step in (M71): the frame callback gone quiet and
// frames pulled by a timer, the camera asked for again.
// Headless Chromium on a development machine is not the hub: use it to compare versions of the code.
import { chromium } from "@playwright/test";
import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i < 0 ? fallback : (process.argv[i + 1] ?? true);
};

/** "90s", "10m", "1h" or plain seconds -> seconds (as tools/benchmark.py --duration). */
export function parseDuration(text) {
  const m = /^(\d+(?:\.\d+)?)([smh]?)$/.exec(String(text).trim());
  if (!m) throw new Error(`bad duration: ${text}`);
  return Number(m[1]) * { "": 1, s: 1, m: 60, h: 3600 }[m[2]];
}

/** One number of the `eval:` section of thresholds.yaml (this script has no YAML parser). */
export function evalThreshold(yaml, key) {
  const section = yaml.slice(yaml.search(/^eval:/m));
  const m = new RegExp(`^  ${key}:\\s*([0-9.]+)`, "m").exec(section);
  if (!m) throw new Error(`eval.${key} not found in thresholds.yaml`);
  return Number(m[1]);
}

/** Least-squares slope of y over t. */
export function slope(points) {
  const n = points.length;
  const mt = points.reduce((a, p) => a + p[0], 0) / n;
  const my = points.reduce((a, p) => a + p[1], 0) / n;
  const den = points.reduce((a, p) => a + (p[0] - mt) ** 2, 0);
  return den ? points.reduce((a, p) => a + (p[0] - mt) * (p[1] - my), 0) / den : 0;
}

/** Samples {t (s), processed, ...} -> one row per whole minute: frames per second over that minute. */
export function perMinute(samples) {
  const rows = [];
  for (let minute = 0; ; minute++) {
    const start = samples.findLast((s) => s.t <= minute * 60 + 1e-6);
    const end = samples.findLast((s) => s.t <= (minute + 1) * 60 + 1e-6);
    if (!start || !end || end.t - start.t < 30) break; // a short last minute says little
    rows.push({ minute, fps: (end.processed - start.processed) / (end.t - start.t) });
  }
  return rows;
}

/** Renderer memory growth in MB / h after the first minute; null under two minutes of run. */
export function rssGrowthMbPerH(samples, skipS = 60) {
  const pts = samples.filter((s) => s.t >= skipS && s.rss_mb?.renderer != null).map((s) => [s.t, s.rss_mb.renderer]);
  return pts.length >= 6 && pts[pts.length - 1][0] - pts[0][0] >= 60 ? slope(pts) * 3600 : null;
}

async function main() {
  const url = arg("url", "http://localhost:5191");
  const seconds = arg("duration", null) ? parseDuration(arg("duration")) : Number(arg("seconds", 30));
  const sampleS = Number(arg("sample-s", 10));
  const camera = arg("camera", null);
  const profile = arg("profile", null); // a browser profile kept between runs: the HTTP cache stays warm
  const args = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"];
  if (camera) args.push(`--use-file-for-fake-video-capture=${camera}`);
  const extra = arg("chrome-args", null); // e.g. --chrome-args "--use-angle=metal --enable-gpu"
  if (extra) args.push(...String(extra).split(" ").filter(Boolean));
  const headless = !process.argv.includes("--headed");

  let browser = null;
  let context;
  if (profile) context = await chromium.launchPersistentContext(String(profile), { args, headless, permissions: ["camera"] });
  else {
    browser = await chromium.launch({ args, headless });
    context = await browser.newContext({ permissions: ["camera"] });
  }
  const page = await context.newPage();
  const problems = [];
  page.on("pageerror", (e) => problems.push(String(e).slice(0, 300)));
  page.on("console", (m) => {
    const t = m.text();
    if (/\[agent\]|Traceback|\[live\]/.test(t)) problems.push(t.slice(0, 400));
  });
  const delegate = arg("delegate", null); // GPU | CPU: force MediaPipe's delegate (the page's localStorage override)
  if (delegate) await page.addInitScript((d) => localStorage.setItem("dg.landmarks.delegate", d), delegate);
  const yolo = arg("yolo", null); // webgpu | wasm: force where the phone detector runs (same kind of override)
  if (yolo) await page.addInitScript((y) => localStorage.setItem("dg.phone.provider", y), yolo);

  await page.goto(`${url}/#/live`);
  await page.getByRole("button", { name: "Dùng thử không lưu" }).click();
  const thinkS = Number(arg("think-s", 0)); // the driver reads the screen this long before pressing start
  if (thinkS > 0) await page.waitForTimeout(thinkS * 1000);
  const pressed = Date.now();
  await page.getByRole("button", { name: "Cho phép camera và bắt đầu" }).click();
  const tech = page.getByRole("button", { name: /chi tiết kỹ thuật/i });
  await tech.waitFor({ timeout: Number(arg("ready-timeout", 300)) * 1000 });
  const startS = (Date.now() - pressed) / 1000; // from pressing start to the loop running
  if (!(await tech.innerText()).startsWith("Ẩn")) await tech.click(); // a kept profile remembers it open
  const card = page.locator("div.fixed.bottom-4");
  const numbers = card.locator("span[data-perf]").first();
  await numbers.waitFor({ timeout: 30_000 });

  // Memory and CPU time of the browser's processes (renderer = the page; gpu = WebGL / WebGPU work).
  const cdp = browser ? await browser.newBrowserCDPSession() : null;
  const processes = async () => {
    if (!cdp) return null;
    const { processInfo } = await cdp.send("SystemInfo.getProcessInfo");
    const rss = new Map();
    try {
      const out = execFileSync("ps", ["-o", "pid=,rss=", "-p", processInfo.map((p) => p.id).join(",")], { encoding: "utf8" });
      for (const line of out.trim().split("\n")) {
        const [pid, kb] = line.trim().split(/\s+/).map(Number);
        rss.set(pid, kb / 1024);
      }
    } catch {
      // ps not available: memory is then not reported
    }
    const by = { rss_mb: {}, cpu_s: {} };
    for (const p of processInfo) {
      by.cpu_s[p.type] = (by.cpu_s[p.type] ?? 0) + p.cpuTime;
      if (rss.has(p.id)) by.rss_mb[p.type] = (by.rss_mb[p.type] ?? 0) + rss.get(p.id);
    }
    return by;
  };

  const read = async () => JSON.parse(await numbers.getAttribute("data-perf"));
  const samples = [];
  const sample = async (began) => {
    const [doc, proc] = await Promise.all([read(), processes()]);
    samples.push({ t: (Date.now() - began) / 1000, ...doc.totals, stages_ms: doc.perf?.stages_ms, ...(proc ?? {}) });
    return doc;
  };
  const began = Date.now();
  let last = await sample(began);
  while ((Date.now() - began) / 1000 < seconds - 0.05) {
    await page.waitForTimeout(Math.min(sampleS, seconds - (Date.now() - began) / 1000) * 1000);
    last = await sample(began);
  }

  const text = await card.innerText();
  const detail = await numbers.getAttribute("title").catch(() => null);
  const isolated = await page.evaluate(() => self.crossOriginIsolated);
  const renderer = await page.evaluate(() => {
    const gl = document.createElement("canvas").getContext("webgl2");
    const ext = gl?.getExtension("WEBGL_debug_renderer_info");
    return gl ? String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)) : "no WebGL2";
  });

  const first = samples[0];
  const end = samples[samples.length - 1];
  const span = end.t - first.t;
  const f = (v, d = 1) => (v == null || !Number.isFinite(v) ? "–" : v.toFixed(d));
  const delivered = end.camera_delivered != null ? end.camera_delivered - first.camera_delivered : null;
  const dropped = end.camera_dropped != null ? end.camera_dropped - first.camera_dropped : null;
  const minutes = perMinute(samples.map((s) => ({ ...s, t: s.t - first.t })));
  const growth = rssGrowthMbPerH(samples.map((s) => ({ ...s, t: s.t - first.t })));
  const cpu = {};
  for (const type of Object.keys(end.cpu_s ?? {})) cpu[type] = (100 * (end.cpu_s[type] - (first.cpu_s?.[type] ?? 0))) / span;
  const summary = {
    label: arg("label", null),
    url,
    webgl: renderer,
    isolated,
    camera: camera ? "file" : "test pattern",
    seconds: span,
    startup_s: startS,
    startup_ms: last.startup,
    fps: (end.processed - first.processed) / span,
    camera_fps: delivered == null ? null : delivered / span,
    camera_delivered: delivered,
    camera_dropped: dropped,
    dropped_pct: delivered ? (100 * dropped) / delivered : null,
    yolo_per_s: (end.yolo_runs - first.yolo_runs) / span,
    minutes,
    lowest_minute_fps: minutes.length ? Math.min(...minutes.map((m) => m.fps)) : null,
    rss_growth_mb_per_h: growth,
    rss_mb: { start: first.rss_mb ?? null, end: end.rss_mb ?? null },
    cpu_pct: cpu,
    last_window: last.perf,
    recovery: last.recovery ?? null, // M71: { pulls, reopens } since the loop started
    problems: [...new Set(problems)],
  };

  console.log(`WebGL: ${renderer}`);
  console.log(`start-up ${f(startS)} s · cross-origin isolated: ${isolated} · camera: ${summary.camera} · ${f(span, 0)} s`);
  console.log(text.split("\n").slice(0, 3).join(" | "));
  console.log(detail ?? "(no timings shown)");
  console.log(
    `Whole run: ${f(summary.fps, 2)} FPS processed` +
      (delivered == null ? "" : ` · camera ${f(summary.camera_fps, 2)} FPS · never processed ${dropped} / ${delivered} (${f(summary.dropped_pct, 2)} %)`) +
      ` · YOLO ${f(summary.yolo_per_s, 2)} runs / s`,
  );
  if (minutes.length) console.log(`FPS per minute: ${minutes.map((m) => f(m.fps)).join(" ")} (lowest ${f(summary.lowest_minute_fps)})`);
  if (end.rss_mb?.renderer != null)
    console.log(
      `Memory (resident): page ${f(first.rss_mb.renderer, 0)} -> ${f(end.rss_mb.renderer, 0)} MB` +
        (end.rss_mb["gpu-process"] != null ? ` · GPU process ${f(first.rss_mb["gpu-process"], 0)} -> ${f(end.rss_mb["gpu-process"], 0)} MB` : "") +
        (growth == null ? "" : ` · page growth after the first minute ${growth >= 0 ? "+" : ""}${f(growth)} MB / h`),
    );
  if (summary.recovery)
    console.log(`Loop watch: frame callback went quiet ${summary.recovery.pulls} time(s), camera asked for again ${summary.recovery.reopens} time(s)`);
  if (Object.keys(cpu).length) console.log(`CPU (100 % = one core): ${Object.entries(cpu).map(([type, pct]) => `${type} ${f(pct, 0)} %`).join(" · ")}`);
  if (span >= 120) {
    const yaml = readFileSync(fileURLToPath(new URL("../../config/thresholds.yaml", import.meta.url)), "utf8");
    const minFps = evalThreshold(yaml, "soak_min_fps");
    const maxGrowth = evalThreshold(yaml, "soak_rss_growth_mb_per_h");
    const verdict = (ok) => (ok == null ? "not judged" : ok ? "PASS" : "FAIL");
    summary.verdict = {
      fps: summary.lowest_minute_fps == null ? null : summary.lowest_minute_fps >= minFps,
      memory: growth == null ? null : growth < maxGrowth,
    };
    console.log(`Verdict: FPS at least ${minFps} in every minute: ${verdict(summary.verdict.fps)} · page memory grows less than ${maxGrowth} MB / h: ${verdict(summary.verdict.memory)}`);
  }
  if (problems.length) console.log("PROBLEMS:\n" + summary.problems.join("\n"));
  const json = arg("json", null);
  if (json) writeFileSync(String(json), JSON.stringify({ summary, samples }, null, 1));
  await (browser ?? context).close();
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await main();
