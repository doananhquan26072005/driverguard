// M58: the pure parts of the redesigned driving screens. Thresholds come from the agent (trip.score_l1/l2).
import { describe, expect, it } from "vitest";
import { durationText, hourMinute } from "../lib/format";
import type { HudSnapshot, HudTrip } from "../lib/types";
import { alertDetail, fatigueBand, fatigueSummary, footerNote, splitAction, trendSlots } from "./hudModel";

const trip = (scores: (number | null)[], window_min = 5): HudTrip => ({
  drive_run_s: 600,
  driving_s: 900,
  score_l1: 40,
  score_l2: 70,
  window_min,
  recent_minutes: scores.map((s, i) => (s == null ? null : { minute: i, drowsy_score: s, max_level: 0 })),
});

describe("M58 driving screens", () => {
  it("words driving time like the design", () => {
    expect(durationText(30)).toBe("Dưới 1 phút");
    expect(durationText(45 * 60)).toBe("45 phút");
    expect(durationText(2 * 3600)).toBe("2 giờ");
    expect(durationText(3600 + 12 * 60 + 40)).toBe("1 giờ 12 phút");
    expect(durationText(2 * 3600 + 5 * 60)).toBe("2 giờ 05 phút");
    expect(durationText(undefined)).toBe("–");
    expect(hourMinute(new Date(2026, 9, 7, 15, 4).getTime() / 1000)).toBe("15:04");
  });

  it("bands fatigue with the trip's own thresholds", () => {
    expect(fatigueBand(39.9, 40, 70)).toBe(0);
    expect(fatigueBand(40, 40, 70)).toBe(1);
    expect(fatigueBand(70, 40, 70)).toBe(2);
    expect(fatigueBand(50, 55, 80)).toBe(0); // tuned thresholds move the bands
  });

  it("pads a short trip on the left and keeps rests as gaps", () => {
    const slots = trendSlots(trip([12, null, 45]));
    expect(slots.map((s) => s.kind)).toEqual(["none", "none", "score", "gap", "score"]);
    expect(slots[4]).toMatchObject({ band: 1, current: true });
    expect(slots[2]).toMatchObject({ current: false });
    expect(trendSlots(undefined)).toEqual([]);
  });

  it("says what the recent minutes mean", () => {
    expect(fatigueSummary(trip([10, 12]), [], true).text).toBe("Thấp · chưa cần nghỉ");
    expect(fatigueSummary(trip([10, 12]), [], false).text).toBe("Thấp · xe đang đỗ");
    expect(fatigueSummary(trip([30, 52, null]), [], true)).toEqual({ band: 1, text: "Mệt · nên nghỉ sớm" });
    expect(fatigueSummary(trip([75]), [], true).band).toBe(2);
    expect(fatigueSummary(trip([20]), ["trend"], true)).toEqual({ band: 1, text: "Mệt · đang tăng dần" });
  });

  it("splits an L3 order into the order and what to do", () => {
    expect(splitAction("Mở mắt! Dừng xe nghỉ ngay")).toEqual(["Mở mắt!", "Dừng xe nghỉ ngay"]);
    expect(splitAction("Ngủ gật nhiều lần: dừng xe nghỉ ngay")).toEqual(["Ngủ gật nhiều lần", "Dừng xe nghỉ ngay"]);
    expect(splitAction("DỪNG XE NGAY!")).toEqual(["DỪNG XE NGAY!", ""]);
  });

  it("writes the L2 detail line from the alert's numbers", () => {
    const at = 1000;
    const t = () => "15:44";
    const n = (v: number) => String(v).replace(".", ",");
    const off = { event_id: "e", level: 2 as const, reasons: ["off_road" as const], at, feedback: null };
    expect(alertDetail({ ...off, metrics: { off_road_s: 2.3, eyes_closed_s: 0, phone_ratio: 0, turn_signal: null } }, t, n)).toBe(
      "Phát hiện lúc 15:44 · nhìn lệch 2,3 giây · không bật xi nhan",
    );
    expect(alertDetail({ ...off, metrics: { off_road_s: 2.3, eyes_closed_s: 0, phone_ratio: 0, turn_signal: "left" } }, t, n)).toContain(
      "xi nhan trái",
    );
    expect(alertDetail({ ...off }, t, n)).toBe("Phát hiện lúc 15:44"); // an agent older than M65
    expect(alertDetail(undefined, t, n)).toBeNull();
  });

  it("puts the most useful note in the bottom bar", () => {
    const snap: HudSnapshot = { connected: true, level: 0, reasons: [], alerts: [] };
    const labels = { signalLost: null, lowFps: "slow", phoneOff: "phone", enroll: null, lastAlert: null };
    expect(footerNote(snap, labels)).toBe("Chưa có cảnh báo nào trong chuyến này");
    expect(footerNote(snap, { ...labels, lastAlert: "last" })).toBe("last");
    expect(footerNote(snap, { ...labels, enroll: "enroll", lastAlert: "last" })).toBe("enroll");
    expect(footerNote({ ...snap, phone_unavailable: true }, { ...labels, enroll: "enroll" })).toBe("phone");
    expect(footerNote({ ...snap, low_fps: true, phone_unavailable: true }, labels)).toBe("slow");
    expect(footerNote({ ...snap, low_fps: true }, { ...labels, signalLost: "lost" })).toBe("lost");
  });
});
