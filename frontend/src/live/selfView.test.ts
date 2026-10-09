// The self-view's place and size (M100): kept inside the window, three sizes, remembered as numbers.
import { describe, expect, it } from "vitest";
import { DEFAULT_PLACE, SELF_VIEW_WIDTHS, clampCorner, parsePlace, resized } from "./selfView";

const WIN = { width: 1280, height: 800 };
const FRAME = { width: 176, height: 200 };

describe("the self-view", () => {
  it("starts where it always was, at the size it always had", () => {
    expect(DEFAULT_PLACE).toEqual({ x: null, y: null, size: 1 });
    expect(SELF_VIEW_WIDTHS[DEFAULT_PLACE.size]).toBe(176);
    expect([...SELF_VIEW_WIDTHS]).toEqual([...SELF_VIEW_WIDTHS].sort((a, b) => a - b));
  });

  it("stays where it was dragged while that is inside the window", () => {
    expect(clampCorner(900, 40, FRAME, WIN)).toEqual({ x: 900, y: 40 });
  });

  it("cannot be dragged out of the window, on any side", () => {
    expect(clampCorner(-500, -500, FRAME, WIN)).toEqual({ x: 8, y: 8 });
    expect(clampCorner(5000, 5000, FRAME, WIN)).toEqual({ x: 1280 - 176 - 8, y: 800 - 200 - 8 });
  });

  it("comes back into view when the window gets smaller than where it was left", () => {
    const small = { width: 390, height: 600 };
    expect(clampCorner(1000, 560, FRAME, small)).toEqual({ x: 390 - 176 - 8, y: 600 - 200 - 8 });
    expect(clampCorner(50, 50, { width: 500, height: 900 }, small)).toEqual({ x: 8, y: 8 }); // larger than the window
  });

  it("has three sizes and stops at either end", () => {
    expect(resized(1, 1)).toBe(2);
    expect(resized(2, 1)).toBe(2);
    expect(resized(1, -1)).toBe(0);
    expect(resized(0, -1)).toBe(0);
  });

  it("reads back what it stored, and takes anything else for the default", () => {
    expect(parsePlace(JSON.stringify({ x: 300, y: 120, size: 2 }))).toEqual({ x: 300, y: 120, size: 2 });
    expect(parsePlace(JSON.stringify({ size: 0 }))).toEqual({ x: null, y: null, size: 0 });
    for (const junk of [null, "", "junk", "7", JSON.stringify({ x: "a", y: 1, size: 9 }), JSON.stringify({ x: 1, y: null, size: 1.5 })])
      expect(parsePlace(junk)).toEqual(DEFAULT_PLACE);
  });
});
