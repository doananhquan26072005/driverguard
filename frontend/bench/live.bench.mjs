// The loop of #/live in a real browser: opens a served build in Chromium with Chrome's fake camera
// and prints the page's own timings ("Chi tiết kỹ thuật", src/live/perf.ts) after a while.
//
//   npx vite build && npx vite preview --port 5191 &
//   node bench/live.bench.mjs --url http://localhost:5191 --seconds 30 [--camera clip.mjpeg] [--headed]
//
// --camera: an .mjpeg / .y4m file Chrome plays as the camera (a public dataset clip, so a face is in
// view); without it Chrome's test pattern (no face). The page is the production build: real
// MediaPipe, real YOLO, Pyodide. Numbers only are read back; nothing is recorded.
// Headless Chromium on a development machine is not the hub: use it to compare versions of the code.
import { chromium } from "@playwright/test";

const arg = (name, fallback) => {
  const i = process.argv.indexOf(`--${name}`);
  return i < 0 ? fallback : (process.argv[i + 1] ?? true);
};
const url = arg("url", "http://localhost:5191");
const seconds = Number(arg("seconds", 30));
const camera = arg("camera", null);
const args = ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"];
if (camera) args.push(`--use-file-for-fake-video-capture=${camera}`);
const extra = arg("chrome-args", null); // e.g. --chrome-args "--use-angle=metal --enable-gpu"
if (extra) args.push(...String(extra).split(" ").filter(Boolean));

const browser = await chromium.launch({ args, headless: !process.argv.includes("--headed") });
const page = await (await browser.newContext({ permissions: ["camera"] })).newPage();
const problems = [];
page.on("pageerror", (e) => problems.push(String(e).slice(0, 300)));
page.on("console", (m) => {
  const t = m.text();
  if (/\[agent\]|Traceback|\[live\]/.test(t)) problems.push(t.slice(0, 400));
});
const delegate = arg("delegate", null); // GPU | CPU: force MediaPipe's delegate (the page's localStorage override)
if (delegate) await page.addInitScript((d) => localStorage.setItem("dg.landmarks.delegate", d), delegate);
const t0 = Date.now();
await page.goto(`${url}/#/live`);
await page.getByRole("button", { name: "Dùng thử không lưu" }).click();
await page.getByRole("button", { name: "Cho phép camera và bắt đầu" }).click();
await page.getByRole("button", { name: /Chi tiết kỹ thuật/ }).click({ timeout: Number(arg("ready-timeout", 300)) * 1000 });
const startS = (Date.now() - t0) / 1000;
await page.waitForTimeout(seconds * 1000);
const card = page.locator("div.fixed.bottom-4");
const text = await card.innerText();
const detail = await card.locator("span[title]").first().getAttribute("title").catch(() => null);
const isolated = await page.evaluate(() => self.crossOriginIsolated);
const renderer = await page.evaluate(() => {
  const gl = document.createElement("canvas").getContext("webgl2");
  const ext = gl?.getExtension("WEBGL_debug_renderer_info");
  return gl ? String(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER)) : "no WebGL2";
});
console.log(`WebGL: ${renderer}`);
console.log(`start-up ${startS.toFixed(1)} s · cross-origin isolated: ${isolated} · camera: ${camera ? "file" : "test pattern"} · ${seconds} s`);
console.log(text.split("\n").slice(0, 3).join(" | "));
console.log(detail ?? "(no timings shown)");
if (problems.length) console.log("PROBLEMS:\n" + [...new Set(problems)].join("\n"));
await browser.close();
