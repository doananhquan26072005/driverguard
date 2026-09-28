import { describe, expect, it } from "vitest";
import { bbox, channelDiff, largestFace, letterboxGeometry, meanLuma, toChw, toPixels } from "./measure";

function image(w: number, h: number, rgb: (x: number, y: number) => [number, number, number]) {
  const px = new Uint8ClampedArray(w * h * 4);
  for (let y = 0; y < h; y++)
    for (let x = 0; x < w; x++) {
      const [r, g, b] = rgb(x, y);
      px.set([r, g, b, 255], (y * w + x) * 4);
    }
  return px;
}

describe("meanLuma", () => {
  it("uses BT.601 weights", () => {
    expect(meanLuma(image(4, 4, () => [255, 0, 0]), 4, 4, null)).toBeCloseTo(76.245, 2);
  });
  it("measures only the face box, whole frame when the box is tiny", () => {
    const px = image(10, 10, (x) => (x < 5 ? [0, 0, 0] : [200, 200, 200]));
    expect(meanLuma(px, 10, 10, [5, 0, 10, 10])).toBeCloseTo(200, 5);
    expect(meanLuma(px, 10, 10, [5, 5, 6, 6])).toBeCloseTo(100, 5);
    expect(meanLuma(px, 10, 10, [-3, -3, 20, 20])).toBeCloseTo(100, 5); // clamped to the image
  });
});

describe("channelDiff", () => {
  it("is 0 for a grey (IR) frame and large for a coloured one", () => {
    expect(channelDiff(image(8, 8, () => [90, 90, 90]), 8, 8)).toBe(0);
    expect(channelDiff(image(8, 8, () => [200, 100, 0]), 8, 8)).toBe(100);
  });
});

describe("letterbox", () => {
  it("matches phone_detector.letterbox for 640x480 into 640", () => {
    expect(letterboxGeometry(640, 480, 640)).toEqual({ scale: 1, w: 640, h: 480, padX: 0, padY: 80 });
  });
  it("converts RGBA to planar RGB / 255", () => {
    const chw = toChw(image(2, 2, () => [255, 51, 0]), 2);
    const expected = [1, 1, 1, 1, 0.2, 0.2, 0.2, 0.2, 0, 0, 0, 0];
    Array.from(chw).forEach((v, i) => expect(v).toBeCloseTo(expected[i], 6));
  });
});

describe("faces", () => {
  it("scales landmarks to pixels, z like x", () => {
    expect(Array.from(toPixels([{ x: 0.5, y: 0.25, z: -0.1 }], 640, 480))).toEqual([
      320,
      120,
      expect.closeTo(-64, 4),
    ]);
  });
  it("picks the largest face as the driver", () => {
    const small = new Float32Array([0, 0, 0, 10, 10, 0]);
    const big = new Float32Array([0, 0, 0, 50, 40, 0]);
    expect(bbox(big)).toEqual([0, 0, 50, 40]);
    expect(largestFace([small, big])).toBe(1);
    expect(largestFace([])).toBe(-1);
  });
});
