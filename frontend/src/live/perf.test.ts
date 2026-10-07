import { describe, expect, it } from "vitest";
import { PerfWindow, summarize } from "./perf";

describe("summarize", () => {
  it("gives p50 / p95 / max of the samples", () => {
    const samples = Array.from({ length: 100 }, (_, i) => i + 1); // 1..100, any order would do
    expect(summarize(samples.reverse())).toEqual({ p50: 51, p95: 96, max: 100 });
  });

  it("has nothing to say without samples", () => {
    expect(summarize([])).toBeNull();
  });
});

describe("PerfWindow", () => {
  it("keeps only the last `size` samples of a stage", () => {
    const w = new PerfWindow(4);
    [100, 100, 1, 2, 3, 4].forEach((ms) => w.add("total", ms));
    const snap = w.snapshot("GPU", 1);
    expect(snap.samples).toBe(4);
    expect(snap.stages_ms.total).toEqual({ p50: 3, p95: 4, max: 4 });
  });

  it("leaves out stages that never ran and ignores broken samples", () => {
    const w = new PerfWindow();
    w.add("python", 1.26);
    w.add("python", Number.NaN);
    w.add("python", -1);
    const snap = w.snapshot("CPU", null);
    expect(Object.keys(snap.stages_ms)).toEqual(["python"]);
    expect(snap.stages_ms.python).toEqual({ p50: 1.3, p95: 1.3, max: 1.3 });
    expect(snap.landmarks_delegate).toBe("CPU");
    expect(snap.yolo_threads).toBeNull();
  });

  it("counts the camera frames the loop never processed", () => {
    const w = new PerfWindow();
    [1, 1, 3, 1, 2].forEach((n) => w.cameraFrames(n)); // 8 delivered, 5 processed
    const snap = w.snapshot(null, null);
    expect(snap.camera_delivered).toBe(8);
    expect(snap.camera_dropped).toBe(3);
  });

  it("says nothing about dropped frames when the browser does not report them", () => {
    const snap = new PerfWindow().snapshot(null, null);
    expect(snap.camera_delivered).toBeNull();
    expect(snap.camera_dropped).toBeNull();
  });
});
