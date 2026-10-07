import { describe, expect, it } from "vitest";
import { YoloPacer } from "./pace";

/** Frames `dt` seconds apart for `seconds`, each jittered by up to +-jitter (deterministic). The
 *  detector answers `inferS` after it took a frame. Returns the times of the frames it took. */
function simulate(targetFps: number, inferS: number, seconds = 20, dt = 1 / 30, jitter = 0.002): number[] {
  const pacer = new YoloPacer(targetFps);
  const taken: number[] = [];
  let busyUntil = -Infinity;
  for (let i = 0; i * dt < seconds; i++) {
    const t = i * dt + jitter * Math.sin(i * 12.9898); // same wobble every run
    if (pacer.take(t, t < busyUntil)) {
      taken.push(t);
      busyUntil = t + inferS;
    }
  }
  return taken;
}

const rate = (taken: number[]) => (taken.length - 1) / (taken[taken.length - 1] - taken[0]);
const gaps = (taken: number[]) => taken.slice(1).map((t, i) => t - taken[i]);

describe("YoloPacer", () => {
  it("runs at the target rate on average, although frames never land exactly on the period", () => {
    expect(rate(simulate(5, 0.09))).toBeCloseTo(5, 1);
    expect(rate(simulate(10, 0.02))).toBeCloseTo(10, 1);
  });

  it("takes the frame nearest the due time: no gap a whole frame longer than the period", () => {
    for (const gap of gaps(simulate(5, 0.09))) {
      expect(gap).toBeGreaterThan(0.2 - 0.02);
      expect(gap).toBeLessThan(0.2 + 0.02);
    }
  });

  it("never takes a frame while the detector is busy: a slow detector runs back to back", () => {
    const taken = simulate(10, 0.25); // 250 ms per run against a period of 100 ms
    for (const gap of gaps(taken)) expect(gap).toBeGreaterThanOrEqual(0.25 - 0.005);
    expect(rate(taken)).toBeGreaterThan(3.5); // the first free frame after each answer
  });

  it("does not run in a burst after a stall", () => {
    const pacer = new YoloPacer(5);
    expect(pacer.take(0, false)).toBe(true);
    // The detector answers only at 1.0 s (five periods late); frames went on meanwhile.
    for (let t = 1 / 30; t < 1; t += 1 / 30) expect(pacer.take(t, true)).toBe(false);
    const after = [];
    for (let t = 1; t < 1.4; t += 1 / 30) if (pacer.take(t, false)) after.push(t);
    expect(after).toHaveLength(2); // at 1.0 and one period later, not five at once
    expect(after[1] - after[0]).toBeGreaterThan(0.18);
  });

  it("never runs when the target is zero", () => {
    expect(simulate(0, 0.01)).toHaveLength(0);
  });

  it("keeps the rate when the camera delivers fewer frames", () => {
    expect(rate(simulate(5, 0.09, 20, 1 / 15))).toBeCloseTo(5, 1);
    expect(rate(simulate(10, 0.02, 20, 1 / 8))).toBeCloseTo(8, 1); // cannot run more often than frames arrive
  });
});
