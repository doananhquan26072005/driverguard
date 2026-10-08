import { describe, expect, it } from "vitest";
import { RepeatCheck } from "./frozen";

const W = 64;
const H = 36;

/** An RGBA frame of pseudo-random pixels (a live sensor: no two frames alike). */
function textured(seed: number, width = W, height = H): Uint8ClampedArray {
  const px = new Uint8ClampedArray(width * height * 4);
  let s = seed * 2654435761 + 1;
  for (let i = 0; i < px.length; i++) {
    s = (s * 1664525 + 1013904223) >>> 0;
    px[i] = i % 4 === 3 ? 255 : s >>> 24;
  }
  return px;
}

function flat(value: number): Uint8ClampedArray {
  return new Uint8ClampedArray(W * H * 4).fill(value);
}

describe("RepeatCheck", () => {
  it("says a repeat for the same image, not for the first one", () => {
    const check = new RepeatCheck(8);
    expect(check.repeated(textured(1), W, H)).toBe(false);
    expect(check.repeated(textured(1), W, H)).toBe(true);
    expect(check.repeated(textured(1), W, H)).toBe(true);
  });

  it("is not fooled by frames that differ, nor by one changed pixel it compares", () => {
    const check = new RepeatCheck(8);
    check.repeated(textured(1), W, H);
    expect(check.repeated(textured(2), W, H)).toBe(false);
    const noisy = textured(2);
    noisy[(8 * W + 16) * 4 + 1] ^= 1; // sensor noise at row 8, column 16
    expect(check.repeated(noisy, W, H)).toBe(false);
    expect(check.repeated(noisy.slice(), W, H)).toBe(true);
  });

  it("never calls an image of one single value a repeat (covered lens: the quality check names it)", () => {
    const check = new RepeatCheck(8);
    for (const value of [0, 0, 0, 255, 255]) expect(check.repeated(flat(value), W, H)).toBe(false);
  });

  it("starts again when the frame size changes", () => {
    const check = new RepeatCheck(8);
    check.repeated(textured(1), W, H);
    expect(check.repeated(textured(1, 32, 18), 32, 18)).toBe(false);
    expect(check.repeated(textured(1, 32, 18), 32, 18)).toBe(true);
  });

  it("is off with stride 0", () => {
    const check = new RepeatCheck(0);
    check.repeated(textured(1), W, H);
    expect(check.repeated(textured(1), W, H)).toBe(false);
  });
});
