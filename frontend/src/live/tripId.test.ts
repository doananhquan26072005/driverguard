import { describe, expect, it } from "vitest";
import { tripId } from "./tripId";

describe("tripId (M82)", () => {
  it("keeps the readable local time and adds a random part", () => {
    expect(tripId(new Date(2026, 9, 8, 7, 5, 9), "a1b2c3")).toBe("trip-20261008-070509-a1b2c3");
  });

  it("differs between two trips started in the same second", () => {
    const at = new Date(2026, 9, 8, 7, 5, 9);
    const ids = new Set(Array.from({ length: 50 }, () => tripId(at)));
    expect(ids.size).toBe(50);
  });

  it("fits the backend's identifier (letters, digits, _ . -, at most 48)", () => {
    expect(tripId()).toMatch(/^trip-\d{8}-\d{6}-[0-9a-f]{6}$/);
    expect(tripId().length).toBeLessThanOrEqual(48);
  });
});
