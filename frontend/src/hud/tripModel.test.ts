import { describe, expect, it } from "vitest";
import type { TripSummary } from "../lib/types";
import { loadingStep } from "../live/agent";
import { DELIVERY_TEXT, driverStory, formatDuration, glanceText, phoneKindText, suggestionText, zoneOf } from "./tripModel";

function trip(over: Partial<TripSummary> = {}): TripSummary {
  return {
    trip_id: "trip-1",
    started_at: "2026-10-01T08:00:00+00:00",
    ended_at: "2026-10-01T10:10:00+00:00",
    duration_s: 7800,
    driving_s: 7200,
    stopped_s: 600,
    rests: 1,
    longest_drive_s: 5400,
    avg_speed_kmh: 62,
    speed_source: "simulated",
    alerts_by_level: { "1": 2, "2": 1, "3": 0 },
    alerts_by_reason: { drowsy_score: 2, off_road: 1 },
    false_alarms: 0,
    microsleeps: 0,
    longest_closure_s: 0.4,
    yawns: 3,
    nods: 0,
    brow_raises: 1,
    off_road_s: 4,
    phone_s: 0,
    monitored_frac: 0.97,
    unavailable_s: 0,
    camera_lost_s: 0,
    enrolled: true,
    driver_changes: 0,
    drowsy_mean: 22,
    drowsy_p90: 45,
    drowsy_max: 58,
    first_tired_min: 95,
    score_l1: 40,
    score_l2: 70,
    rating: "attention",
    rating_reasons: ["tired_minutes"],
    suggestions: [{ code: "rest_after", minutes: 85 }],
    minutes: [],
    ...over,
  };
}

describe("trip summary words", () => {
  it("formats durations the way a driver says them", () => {
    expect(formatDuration(40)).toBe("40 giây");
    expect(formatDuration(25 * 60)).toBe("25 phút");
    expect(formatDuration(7800)).toBe("2 giờ 10 phút");
    expect(formatDuration(7200)).toBe("2 giờ");
  });

  it("tells the trip as a short story, no variable names", () => {
    const story = driverStory(trip());
    expect(story).toBe(
      "Chuyến 2 giờ 10 phút, nghỉ 1 lần. Bạn có dấu hiệu mệt từ phút lái thứ 95. Có 2 lần nhắc nghỉ, 1 lần nhắc nhìn đường.",
    );
    expect(story).not.toMatch(/drowsy|L[0-3]|EAR|PERCLOS/);
    expect(driverStory(trip({ alerts_by_reason: {}, first_tired_min: null, rests: 0 }))).toBe(
      "Chuyến 2 giờ 10 phút, không nghỉ lần nào. Không có lần nhắc nào.",
    );
  });

  it("words suggestions with their numbers", () => {
    expect(suggestionText("rest_after", 85)).toBe("Lần sau nên dừng nghỉ sau khoảng 1 giờ 25 phút lái.");
    expect(suggestionText("regular_breaks", 120)).toContain("2 giờ");
  });

  it("splits the per-minute chart in three zones at the trip's L1 / L2", () => {
    expect([zoneOf(10, 40, 70), zoneOf(40, 40, 70), zoneOf(75, 40, 70)]).toEqual(["awake", "tired", "very_tired"]);
  });

  it("says honestly where the summary went", () => {
    expect(DELIVERY_TEXT.failed).toMatch(/Chưa gửi được/);
    expect(DELIVERY_TEXT.local).toMatch(/không được gửi/);
  });
});

describe("#/live start-up steps", () => {
  it("shows two steps, the downloads as one with its own progress", () => {
    expect(loadingStep(false, 0, 3)).toEqual({ step: "camera", progress: 0 });
    expect(loadingStep(true, 0, 3)).toEqual({ step: "prepare", progress: 0 });
    expect(loadingStep(true, 2, 3).progress).toBeCloseTo(2 / 3);
  });

  it("the downloads run behind the camera question (M50): done ones show once the camera is on", () => {
    expect(loadingStep(false, 3, 3)).toEqual({ step: "camera", progress: 0 }); // all loaded, still asking
    expect(loadingStep(true, 3, 3)).toEqual({ step: "prepare", progress: 1 });
  });
});

describe("block 8 measurements in the trip report (M38)", () => {
  it("splits phone time into call / text / unknown", () => {
    expect(phoneKindText(trip({ phone_s: 20, phone_call_s: 12, phone_text_s: 5 }))).toBe("12 s gọi / 5 s nhắn tin / 3 s không rõ");
    expect(phoneKindText(trip({ phone_s: 8, phone_call_s: 0, phone_text_s: 8 }))).toBe("0 s gọi / 8 s nhắn tin");
  });

  it("says the glances are measured only", () => {
    const text = glanceText(trip({ glances: 14, off_road_ratio_max: 0.62 }));
    expect(text).toContain("14 lần");
    expect(text).toContain("62%");
    expect(text).toContain("chưa cảnh báo");
  });

  it("shows a dash for summaries stored before M38", () => {
    expect(phoneKindText(trip())).toBe("–");
    expect(glanceText(trip())).toBe("–");
  });
});
