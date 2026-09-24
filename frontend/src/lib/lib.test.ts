import { describe, expect, it } from "vitest";
import { demoSnapshot, DEMO_SCRIPT } from "../hud/demo";
import { ago, changedValues, clockText, formatPercent, query, rangeStart } from "./format";
import { linearScale, nearestIndex, niceTicks, timeTicks } from "./scale";

describe("scale", () => {
  it("maps and inverts linearly", () => {
    const s = linearScale([0, 100], [300, 0]);
    expect(s(0)).toBe(300);
    expect(s(40)).toBe(180);
    expect(s.invert(180)).toBe(40);
  });

  it("makes clean ticks", () => {
    expect(niceTicks(0, 100, 5)).toEqual([0, 20, 40, 60, 80, 100]);
    expect(niceTicks(0, 1, 4)).toEqual([0, 0.5, 1]);
    expect(niceTicks(5, 5)).toEqual([5]);
  });

  it("puts time ticks on round minutes", () => {
    const start = Date.parse("2026-09-24T08:03:20Z");
    const ticks = timeTicks(start, start + 40 * 60_000, 5);
    expect(ticks.length).toBeGreaterThanOrEqual(3);
    expect(ticks.length).toBeLessThanOrEqual(6);
    for (const t of ticks) expect(new Date(t).getSeconds()).toBe(0);
    expect(ticks[0]).toBeGreaterThanOrEqual(start);
  });

  it("finds the nearest point", () => {
    expect(nearestIndex([], 5)).toBe(-1);
    expect(nearestIndex([0, 10, 20], 14)).toBe(1);
    expect(nearestIndex([0, 10, 20], 16)).toBe(2);
    expect(nearestIndex([0, 10, 20], -50)).toBe(0);
  });
});

describe("format", () => {
  it("formats small things", () => {
    expect(formatPercent(0.125, 1)).toBe("12,5%");
    expect(formatPercent(null)).toBe("–");
    expect(clockText(2.5)).toBe("02:30");
    expect(clockText(undefined)).toBe("--:--");
    expect(ago(12)).toBe("12 giây trước");
    expect(ago(125)).toBe("2 phút trước");
  });

  it("builds query strings without empty values", () => {
    expect(query({ a: 1, b: "", c: undefined, d: false, e: true })).toBe("?a=1&e=true");
    expect(query({})).toBe("");
  });

  it("computes range starts", () => {
    const now = Date.parse("2026-09-24T12:00:00Z");
    expect(rangeStart("24h", now)).toBe("2026-09-23T12:00:00.000Z");
    expect(rangeStart("all", now)).toBeUndefined();
  });

  it("sends only changed, valid threshold values", () => {
    const stored = { "risk.drowsy.l1": 40, "alert.fall_hold_s": 3 };
    const r = changedValues({ "risk.drowsy.l1": "40", "alert.fall_hold_s": "4,5", "risk.drowsy.l2": "", x: "abc" }, stored);
    expect(r.values).toEqual({ "alert.fall_hold_s": 4.5 });
    expect(r.invalid).toEqual(["x"]);
  });
});

describe("HUD demo script", () => {
  it("follows the scripted levels", () => {
    const none = new Set<string>();
    expect(demoSnapshot(5, none).level).toBe(0);
    for (const ep of DEMO_SCRIPT) {
      const s = demoSnapshot(ep.start + 1, none);
      expect(s.level).toBe(ep.level);
      expect(s.reasons).toEqual(ep.reasons);
      expect(s.alerts[0].level).toBe(ep.level); // newest alert first
    }
    expect(demoSnapshot(65, none).alerts).toEqual([]); // new cycle, no alerts yet
  });

  it("marks flagged alerts", () => {
    const s = demoSnapshot(27, new Set(["demo-0-1"]));
    expect(s.alerts[0].event_id).toBe("demo-0-1");
    expect(s.alerts[0].feedback).toBe("false_alarm");
    expect(s.alerts[1].feedback).toBeNull();
  });
});
