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

describe("M58 trip summary screen", () => {
  it("words suggestions as tiles", async () => {
    const { suggestionTile } = await import("./tripModel");
    expect(suggestionTile("rest_after", 85)).toEqual({ value: "Nghỉ sau ~1 giờ 25 phút", label: "Lần sau nên dừng nghỉ" });
    expect(suggestionTile("eyes_on_road").value).toBe("Giữ mắt nhìn đường");
  });

  it("groups a long trip into at most 65 bars and greys the stops", async () => {
    const { summaryBars } = await import("./tripModel");
    const { demoTripSummary } = await import("./demo");
    const s = demoTripSummary(); // 130 minutes, stopped 70-79, tired from 95
    const { perBar, bars } = summaryBars(s);
    expect(perBar).toBe(2);
    expect(bars).toHaveLength(65);
    expect(bars[36].stopped).toBe(true); // minutes 72-73
    expect(bars[0].zone).toBe("awake");
    expect(bars.at(-1)?.zone).toBe("tired");
    expect(summaryBars({ ...s, minutes: s.minutes.slice(0, 10) }).perBar).toBe(1);
  });
});

describe("M58 HUD stage", () => {
  it("scales the 1280 x 800 design on landscape screens and keeps phones fluid", async () => {
    const { stageScale } = await import("./HudStage");
    expect(stageScale(1280, 800)).toBe(1);
    expect(stageScale(2000, 1350)).toBeCloseTo(1.5625); // width-bound: letterboxed top and bottom
    expect(stageScale(1440, 720)).toBe(0.9); // short screen: height-bound, nothing overflows
    expect(stageScale(390, 844)).toBeNull(); // phone
    expect(stageScale(1024, 1366)).toBeNull(); // portrait tablet
  });
});

describe("M58 review: numbers in plain words", () => {
  it("says drowsiness, attention and the eyes in words", async () => {
    const { drowsyWord, attentionWord, eyesWord } = await import("./hudModel");
    const n = (v: number) => String(v).replace(".", ",");
    expect(drowsyWord(12, 40, 70)).toEqual({ word: "Tỉnh táo", tone: "ok" });
    expect(drowsyWord(52, 40, 70)).toEqual({ word: "Hơi mệt", tone: "caution" });
    expect(drowsyWord(71, 40, 70).word).toBe("Rất mệt");
    expect(attentionWord([], 0)).toEqual({ word: "Tập trung", tone: "ok" });
    expect(attentionWord(["phone", "off_road"], 2)).toEqual({ word: "Cầm điện thoại", tone: "danger" });
    expect(attentionWord(["off_road"], 2).word).toBe("Nhìn lệch");
    expect(eyesWord(0.2, n)).toEqual({ word: "Đang mở", tone: "ok" }); // a blink
    expect(eyesWord(0.8, n)).toEqual({ word: "Nhắm 0,8 giây", tone: "caution" });
    expect(eyesWord(2.4, n).tone).toBe("danger");
  });
});

describe("Vietnamese voice", () => {
  it("never speaks Vietnamese with an English voice", async () => {
    const { pickVietnameseVoice } = await import("./chime");
    const v = (lang: string, localService = true, name = lang) => ({ lang, localService, name });
    expect(pickVietnameseVoice([v("en-US"), v("en-GB")])).toBeNull();
    expect(pickVietnameseVoice([v("en-US"), v("vi-VN")])?.lang).toBe("vi-VN");
    expect(pickVietnameseVoice([v("vi-VN", false, "online"), v("vi-VN", true, "local")])?.name).toBe("local");
    expect(pickVietnameseVoice([v("vi"), v("vi_VN")])?.lang).toBe("vi_VN");
  });
});
