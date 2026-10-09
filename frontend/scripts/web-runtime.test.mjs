// The script that puts Pyodide and MediaPipe next to the app (M99): what it copies, and that a package
// whose bytes are not those of the lock file is never written. Fake node_modules, no network.
import { mkdtemp, mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { MEDIAPIPE_FILES, PYODIDE_FILES, prepare, releaseUrl, sha256, verified, wheels } from "./web-runtime.mjs";

const NUMPY = Buffer.from("numpy wheel");
const YAML = Buffer.from("pyyaml wheel");
const DEP = Buffer.from("a dependency");
const lock = {
  packages: {
    numpy: { file_name: "numpy.whl", sha256: sha256(NUMPY), depends: ["dep"] },
    pyyaml: { file_name: "pyyaml.whl", sha256: sha256(YAML), depends: [] },
    dep: { file_name: "dep.whl", sha256: sha256(DEP), depends: [] },
    other: { file_name: "other.whl", sha256: "0", depends: [] },
  },
};

async function fakeModules() {
  const root = await mkdtemp(join(tmpdir(), "dg-runtime-"));
  const pyodide = join(root, "node_modules", "pyodide");
  const wasm = join(root, "node_modules", "@mediapipe", "tasks-vision", "wasm");
  await mkdir(pyodide, { recursive: true });
  await mkdir(wasm, { recursive: true });
  await writeFile(join(pyodide, "package.json"), JSON.stringify({ version: "9.9.9" }));
  for (const f of PYODIDE_FILES) await writeFile(join(pyodide, f), f === "pyodide-lock.json" ? JSON.stringify(lock) : `core ${f}`);
  for (const f of [...MEDIAPIPE_FILES, "vision_wasm_module_internal.wasm"]) await writeFile(join(wasm, f), `wasm ${f}`);
  return { modules: join(root, "node_modules"), dest: join(root, "public", "runtime") };
}

const cdn = (files) => {
  const asked = [];
  const download = async (url) => {
    asked.push(url);
    const name = url.split("/").pop();
    if (!(name in files)) throw new Error(`${url}: HTTP 404`);
    return files[name];
  };
  return { asked, download };
};

describe("web-runtime", () => {
  it("asks the lock file for the packages and what they depend on, once each", () => {
    expect(wheels(lock, ["numpy", "pyyaml", "numpy"]).map((w) => w.file)).toEqual(["numpy.whl", "dep.whl", "pyyaml.whl"]);
    expect(() => wheels(lock, ["scipy"])).toThrow(/no package "scipy"/);
  });

  it("copies the runtime from node_modules and downloads only the packages, from the release of that version", async () => {
    const { modules, dest } = await fakeModules();
    const { asked, download } = cdn({ "numpy.whl": NUMPY, "dep.whl": DEP, "pyyaml.whl": YAML });
    expect(await prepare(dest, modules, download)).toEqual({ version: "9.9.9", downloaded: 3 });
    expect(asked).toEqual(["numpy.whl", "dep.whl", "pyyaml.whl"].map((f) => releaseUrl("9.9.9") + f));
    expect((await readdir(join(dest, "pyodide"))).sort()).toEqual([...PYODIDE_FILES, "numpy.whl", "dep.whl", "pyyaml.whl"].sort());
    expect((await readdir(join(dest, "mediapipe"))).sort()).toEqual([...MEDIAPIPE_FILES].sort()); // not the module build
    expect(await readFile(join(dest, "pyodide", "numpy.whl"))).toEqual(NUMPY);
  });

  it("a second run downloads nothing; a file that was changed on disk is fetched again", async () => {
    const { modules, dest } = await fakeModules();
    const first = cdn({ "numpy.whl": NUMPY, "dep.whl": DEP, "pyyaml.whl": YAML });
    await prepare(dest, modules, first.download);
    const again = cdn({});
    expect((await prepare(dest, modules, again.download)).downloaded).toBe(0);
    expect(again.asked).toEqual([]);
    await writeFile(join(dest, "pyodide", "dep.whl"), "tampered");
    const repair = cdn({ "dep.whl": DEP });
    expect((await prepare(dest, modules, repair.download)).downloaded).toBe(1);
    expect(await readFile(join(dest, "pyodide", "dep.whl"))).toEqual(DEP);
  });

  it("a package whose bytes are not those of the lock file is refused and not written", async () => {
    const { modules, dest } = await fakeModules();
    const { download } = cdn({ "numpy.whl": Buffer.from("something else"), "dep.whl": DEP, "pyyaml.whl": YAML });
    await expect(prepare(dest, modules, download)).rejects.toThrow(/numpy\.whl: sha256 .* Not written/);
    expect(await readdir(join(dest, "pyodide"))).not.toContain("numpy.whl");
    expect(() => verified(NUMPY, { file: "numpy.whl", sha256: sha256(YAML) })).toThrow();
    expect(verified(NUMPY, { file: "numpy.whl", sha256: sha256(NUMPY) })).toBe(NUMPY);
  });
});
