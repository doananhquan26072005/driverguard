import { describe, expect, it } from "vitest";
import { EYES, FACE_EDGES, NOSE_LINE, angleText, boxColor, coverView, faceBox, irisLine, toCanvas } from "./faceDrawing";

const points = (pairs: Record<number, [number, number]>) => {
  const p = new Float32Array(478 * 3).fill(NaN);
  for (const [i, [x, y]] of Object.entries(pairs)) {
    p[Number(i) * 3] = x;
    p[Number(i) * 3 + 1] = y;
    p[Number(i) * 3 + 2] = 0;
  }
  return p;
};

describe("face drawing (M104)", () => {
  it("draws only points of the 478-point mesh", () => {
    expect(FACE_EDGES.length).toBeGreaterThan(100);
    for (const e of FACE_EDGES) expect(Math.max(e.start, e.end)).toBeLessThan(478);
    for (const i of [...NOSE_LINE, ...EYES.flatMap((e) => [e.iris, ...e.corners])]) expect(i).toBeLessThan(478);
  });

  it("places the frame as object-fit: cover does, and mirrors it like the video", () => {
    const v = coverView(640, 480, 320, 240); // same shape: half size, nothing cut
    expect(v).toEqual({ scale: 0.5, dx: 0, dy: 0, width: 320 });
    expect(toCanvas(v, 0, 0)).toEqual([320, 0]); // the frame's left edge is the picture's right edge
    expect(toCanvas(v, 640, 480)).toEqual([0, 240]);
    const wide = coverView(640, 480, 400, 240); // wider box: the frame's top and bottom are cut
    expect(wide.scale).toBeCloseTo(400 / 640);
    expect(wide.dy).toBeCloseTo((240 - 480 * (400 / 640)) / 2);
  });

  it("boxes the landmarks, skipping a point that is not a number", () => {
    expect(faceBox(points({ 1: [10, 20], 2: [30, 5], 3: [15, 40] }))).toEqual([10, 5, 30, 40]);
  });

  it("writes the head's angles, a dash for one not measured", () => {
    expect(angleText(15.4, 9.6, -0.2)).toBe("(15°, 10°, 0°)");
    expect(angleText(null, 3, null)).toBe("(–, 3°, –)");
  });

  it("colours the box by level, as the HUD", () => {
    expect([0, 1, 2, 3].map(boxColor)).toEqual(["#facc15", "#fb923c", "#fb923c", "#ef4444"]);
  });

  it("draws the iris's line away from the middle of the eye, never shorter than a third of the eye", () => {
    const eye = EYES[0];
    const p = points({ [eye.corners[0]]: [100, 100], [eye.corners[1]]: [140, 100], [eye.iris]: [124, 100] });
    const [x1, y1, x2, y2] = irisLine(p, eye, 4)!;
    expect([x1, y1]).toEqual([124, 100]);
    expect(x2).toBeCloseTo(124 + 16); // offset 4 px x 4
    expect(y2).toBeCloseTo(100);
    const centred = points({ [eye.corners[0]]: [100, 100], [eye.corners[1]]: [140, 100], [eye.iris]: [120, 100] });
    expect(irisLine(centred, eye, 4)).toBeNull(); // straight on: nothing to show
    const slight = points({ [eye.corners[0]]: [100, 100], [eye.corners[1]]: [140, 100], [eye.iris]: [120, 101] });
    expect(irisLine(slight, eye, 4)![3]).toBeCloseTo(101 + 12); // 0.3 x the eye's 40 px
  });
});
