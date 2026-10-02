import { describe, expect, it } from "vitest";
import { ALARM_REPEAT_S, alertSound, armAudio, play, systemSound } from "../hud/chime";
import { DEMO_CYCLE_S, demoSnapshot, DEMO_SCRIPT } from "../hud/demo";
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
    expect(demoSnapshot(DEMO_CYCLE_S + 5, none).alerts).toEqual([]); // new cycle, no alerts yet
  });

  it("marks flagged alerts", () => {
    const s = demoSnapshot(25, new Set(["demo-0-1"]));
    expect(s.alerts[0].event_id).toBe("demo-0-1");
    expect(s.alerts[0].feedback).toBe("false_alarm");
    expect(s.alerts[1].feedback).toBeNull();
  });
});

describe("HUD alert sounds", () => {
  const signature = (level: 0 | 1 | 2 | 3, reason: Parameters<typeof alertSound>[1][number]) => {
    const s = alertSound(level, [reason]);
    return s && JSON.stringify(s.notes);
  };

  it("gives each kind of alert its own sound", () => {
    const kinds = ["drowsy_score", "trend", "microsleep", "off_road", "phone", "no_face"] as const;
    const l2 = kinds.map((r) => signature(2, r));
    expect(new Set(l2).size).toBe(kinds.length);
    expect(alertSound(2, ["phone"])?.kind).toBe("phone");
    expect(alertSound(1, ["microsleep"])?.kind).toBe("microsleep"); // red light: capped at L1
    expect(alertSound(2, ["blink_rate"])?.kind).toBe("drowsy");
  });

  it("uses the reason that raised the alert and the level for volume", () => {
    // L2 off_road active, then phone: the alert manager puts the new reason first.
    expect(alertSound(2, ["phone", "off_road"])?.kind).toBe("phone");
    const gains = ([1, 2, 3] as const).map((lv) => alertSound(lv, ["drowsy_score"])!.gain);
    expect(gains[0]).toBeLessThan(gains[1]);
    expect(gains[1]).toBeLessThan(gains[2]);
    expect(alertSound(0, ["phone"])).toBeNull();
  });

  it("makes L3 a siren, whatever the reason", () => {
    const s = alertSound(3, ["microsleep", "drowsy_score"])!;
    expect(s.kind).toBe("alarm");
    const end = Math.max(...s.notes.map((n) => n.at + n.dur));
    expect(end).toBeLessThan(ALARM_REPEAT_S); // one siren ends before the next repeat
  });

  it("has a loud, distinct sound when monitoring stops (M28)", () => {
    const stop = systemSound("monitoring_stopped");
    expect(stop.gain).toBe(systemSound("camera_lost").gain);
    expect(stop.notes).not.toEqual(systemSound("camera_lost").notes);
    expect(stop.notes).not.toEqual(systemSound("monitoring_unavailable").notes);
  });

  it("has a loud, distinct sound when the vehicle signal is lost while driving (M26)", () => {
    const lost = systemSound("vehicle_signal_lost");
    expect(lost.gain).toBe(systemSound("camera_lost").gain);
    expect(lost.notes).not.toEqual(systemSound("camera_lost").notes);
    expect(lost.notes).not.toEqual(systemSound("vehicle_signal_restored").notes);
    expect(systemSound("vehicle_signal_restored").gain).toBeLessThan(lost.gain);
  });

  it("has distinct system sounds for the camera", () => {
    expect(systemSound("camera_lost").kind).toBe("camera_lost");
    expect(JSON.stringify(systemSound("camera_lost").notes)).not.toBe(JSON.stringify(systemSound("camera_restored").notes));
  });

  it("demo plays every kind of alert", () => {
    const reasons = new Set(DEMO_SCRIPT.flatMap((e) => e.reasons));
    for (const r of ["drowsy_score", "off_road", "phone", "microsleep", "trend"]) expect(reasons.has(r as never)).toBe(true);
    expect(Math.max(...DEMO_SCRIPT.map((e) => e.end))).toBeLessThanOrEqual(DEMO_CYCLE_S);
  });

  it("demo loses the face once: monitoring unavailable, no alert (FR-6)", () => {
    const s = demoSnapshot(48, new Set());
    expect(s.unavailable).toBe(true);
    expect(s.level).toBe(0);
    expect(demoSnapshot(30, new Set()).unavailable).toBe(false);
    expect(systemSound("monitoring_unavailable").notes).not.toEqual(systemSound("monitoring_restored").notes);
  });
});

describe("HUD sound always on", () => {
  it("reports sound as blocked where there is no audio, and plays nothing", () => {
    // jsdom / node has no AudioContext: the HUD shows the touch-to-enable strip instead of failing.
    let on: boolean | null = null;
    const cleanup = armAudio((v) => (on = v));
    expect(on).toBe(false);
    expect(() => play(alertSound(3, ["microsleep"]))).not.toThrow();
    cleanup();
  });
});
