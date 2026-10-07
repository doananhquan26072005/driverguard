// The arithmetic of the long run of bench/live.bench.mjs, on made-up samples (no browser).
import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { evalThreshold, parseDuration, perMinute, rssGrowthMbPerH, slope } from "./live.bench.mjs";

/** One sample every 10 s for `seconds`, at `fps(t)` frames per second, renderer memory `rss(t)` MB. */
function run(seconds, fps, rss = () => 500) {
  const samples = [];
  let processed = 0;
  for (let t = 0; t <= seconds; t += 10) {
    if (t > 0) processed += 10 * fps(t);
    samples.push({ t, processed, rss_mb: { renderer: rss(t) } });
  }
  return samples;
}

describe("parseDuration", () => {
  it("reads seconds, minutes and hours", () => {
    expect([parseDuration("90s"), parseDuration("10m"), parseDuration("1h"), parseDuration("45")]).toEqual([90, 600, 3600, 45]);
    expect(() => parseDuration("soon")).toThrow();
  });
});

describe("evalThreshold", () => {
  it("reads the two soak limits from the real thresholds.yaml", () => {
    const yaml = readFileSync(new URL("../../config/thresholds.yaml", import.meta.url), "utf8");
    expect(evalThreshold(yaml, "soak_min_fps")).toBeGreaterThan(0);
    expect(evalThreshold(yaml, "soak_rss_growth_mb_per_h")).toBeGreaterThan(0);
  });

  it("only looks inside the eval section and fails on a missing key", () => {
    const yaml = "phone:\n  soak_min_fps: 99\neval:\n  soak_min_fps: 15\n";
    expect(evalThreshold(yaml, "soak_min_fps")).toBe(15);
    expect(() => evalThreshold(yaml, "nothing")).toThrow();
  });
});

describe("perMinute", () => {
  it("gives the frame rate of each whole minute, so one slow minute shows", () => {
    const rows = perMinute(run(180, (t) => (t > 60 && t <= 120 ? 12 : 30)));
    expect(rows.map((r) => Math.round(r.fps))).toEqual([30, 12, 30]);
  });

  it("leaves out a last minute shorter than 30 s", () => {
    expect(perMinute(run(80, () => 30))).toHaveLength(1);
    expect(perMinute(run(20, () => 30))).toHaveLength(0);
  });
});

describe("rssGrowthMbPerH", () => {
  it("is the slope after the first minute, in MB per hour", () => {
    // 100 MB while loading in the first minute, then 1 MB per minute = 60 MB / h
    const samples = run(600, () => 30, (t) => (t < 60 ? 400 + t : 500 + (t - 60) / 60));
    expect(rssGrowthMbPerH(samples)).toBeCloseTo(60, 3);
  });

  it("is flat for constant memory and unknown for a short run or without memory readings", () => {
    expect(rssGrowthMbPerH(run(600, () => 30))).toBeCloseTo(0, 6);
    expect(rssGrowthMbPerH(run(90, () => 30))).toBeNull();
    expect(rssGrowthMbPerH(run(600, () => 30).map((s) => ({ ...s, rss_mb: undefined })))).toBeNull();
  });
});

describe("slope", () => {
  it("is zero for a single time", () => {
    expect(slope([[5, 1], [5, 3]])).toBe(0);
  });
});
