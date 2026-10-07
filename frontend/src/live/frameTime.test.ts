import { describe, expect, it } from "vitest";
import { frameTimeMs, MAX_FRAME_AGE_MS } from "./frameTime";

describe("frameTimeMs (M50)", () => {
  it("is the capture time when the browser gives one", () => {
    expect(frameTimeMs(1000, { captureTime: 950, presentationTime: 980 }, 900)).toBe(950);
  });

  it("falls back to the presentation time, then to now", () => {
    expect(frameTimeMs(1000, { presentationTime: 980 }, 900)).toBe(980);
    expect(frameTimeMs(1000, {}, 900)).toBe(1000);
    expect(frameTimeMs(1000, undefined, 900)).toBe(1000); // requestAnimationFrame: no metadata
  });

  it("does not believe a time in the future, too old, or not after the previous frame", () => {
    expect(frameTimeMs(1000, { captureTime: 1005 }, 900)).toBe(1000);
    expect(frameTimeMs(5000, { captureTime: 5000 - MAX_FRAME_AGE_MS - 1 }, 900)).toBe(5000);
    expect(frameTimeMs(1000, { captureTime: 900, presentationTime: 990 }, 900)).toBe(990); // same frame time twice
    expect(frameTimeMs(1000, { captureTime: Number.NaN }, 900)).toBe(1000);
  });

  it("keeps the camera's own rhythm when processing is uneven", () => {
    // Frames captured every 33 ms, processed 5 to 60 ms late: the durations stay 33 ms.
    const lateness = [5, 60, 12, 48, 7];
    let last = -Infinity;
    const times = lateness.map((late, i) => (last = frameTimeMs(i * 33 + late, { captureTime: i * 33 }, last)));
    expect(times).toEqual([0, 33, 66, 99, 132]);
  });
});
