// Put the two runtimes #/live needs next to the app, so the page loads them from its own origin (M99;
// audit 08/10, A4 H3). Before, Pyodide and MediaPipe's wasm came from cdn.jsdelivr.net at run time, with
// no integrity check, into the page that holds the camera stream and the login token.
//
//   node scripts/web-runtime.mjs [public/runtime]        (part of `npm run prepare-live`)
//
// - pyodide/:   the runtime itself is copied from node_modules/pyodide (the exact version of
//               package.json, its integrity kept by package-lock.json). The Python packages the agent
//               imports are not in the npm package: they are downloaded once from the Pyodide release
//               and checked against the sha256 of pyodide-lock.json, which did come from npm. A file
//               already there with the right sha256 is not downloaded again.
// - mediapipe/: the wasm builds of @mediapipe/tasks-vision, copied from node_modules.
// Nothing here is an image; these are code and wasm only.
import { createHash } from "node:crypto";
import { copyFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const PYTHON_PACKAGES = ["numpy", "pyyaml"]; // frontend/src/live/agent.ts PYODIDE_PACKAGES
export const PYODIDE_FILES = ["pyodide.mjs", "pyodide.asm.js", "pyodide.asm.wasm", "python_stdlib.zip", "pyodide-lock.json"];
// The loader MediaPipe picks by itself: SIMD where the browser has it, else the plain build.
export const MEDIAPIPE_FILES = ["vision_wasm_internal.js", "vision_wasm_internal.wasm", "vision_wasm_nosimd_internal.js", "vision_wasm_nosimd_internal.wasm"];

export const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

/** Where a Pyodide release keeps its packages. */
export const releaseUrl = (version) => `https://cdn.jsdelivr.net/pyodide/v${version}/full/`;

/** The wheels to fetch for `names` and what they need, from pyodide-lock.json: [{ file, sha256 }]. */
export function wheels(lock, names) {
  const out = new Map();
  const add = (name) => {
    const pkg = lock.packages[name];
    if (!pkg) throw new Error(`pyodide-lock.json has no package "${name}"`);
    if (out.has(pkg.file_name)) return;
    out.set(pkg.file_name, { file: pkg.file_name, sha256: pkg.sha256 });
    for (const dep of pkg.depends ?? []) add(dep);
  };
  names.forEach(add);
  return [...out.values()];
}

/** The bytes when they are what the lock file says, else an error that names both fingerprints. */
export function verified(bytes, wheel) {
  const got = sha256(bytes);
  if (got !== wheel.sha256) throw new Error(`${wheel.file}: sha256 ${got}, the lock file says ${wheel.sha256}. Not written.`);
  return bytes;
}

async function existing(path) {
  try {
    return await readFile(path);
  } catch {
    return null;
  }
}

export async function prepare(dest, modules, download = (url) => fetch(url).then(async (r) => {
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return Buffer.from(await r.arrayBuffer());
})) {
  const pyodide = join(modules, "pyodide");
  const version = JSON.parse(await readFile(join(pyodide, "package.json"), "utf8")).version;
  await mkdir(join(dest, "pyodide"), { recursive: true });
  for (const f of PYODIDE_FILES) await copyFile(join(pyodide, f), join(dest, "pyodide", f));
  const lock = JSON.parse(await readFile(join(pyodide, "pyodide-lock.json"), "utf8"));
  let downloaded = 0;
  for (const wheel of wheels(lock, PYTHON_PACKAGES)) {
    const path = join(dest, "pyodide", wheel.file);
    const have = await existing(path);
    if (have && sha256(have) === wheel.sha256) continue;
    await writeFile(path, verified(await download(releaseUrl(version) + wheel.file), wheel));
    downloaded += 1;
  }
  await mkdir(join(dest, "mediapipe"), { recursive: true });
  const wasm = join(modules, "@mediapipe", "tasks-vision", "wasm");
  for (const f of MEDIAPIPE_FILES) await copyFile(join(wasm, f), join(dest, "mediapipe", f));
  return { version, downloaded };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
  const dest = resolve(root, process.argv[2] ?? "public/runtime");
  const { version, downloaded } = await prepare(dest, join(root, "node_modules"));
  console.log(`${dest}: Pyodide ${version} (${downloaded} package(s) downloaded and checked), MediaPipe wasm`);
}
