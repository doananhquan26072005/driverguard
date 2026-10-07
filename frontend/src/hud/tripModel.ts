// Words for the end-of-trip summary (edge_agent/decision/trip_summary.py). Pure, unit-tested in
// tripModel.test.ts. The driver version uses plain sentences, no variable names; the assessment
// describes the trip, it does not grade the driver (alerts can be false).
import type { RatingReason, SuggestionCode, TripDelivery, TripRating, TripSummary } from "../lib/types";

export const RATING_TEXT: Record<TripRating, { title: string; detail: string }> = {
  good: { title: "Chuyến đi an toàn", detail: "Không thấy dấu hiệu đáng lo trong chuyến này." },
  attention: { title: "Cần chú ý", detail: "Có dấu hiệu mệt hoặc mất tập trung trong chuyến này." },
  risk: { title: "Có lúc rất nguy hiểm", detail: "Đã có lúc nhắm mắt ngủ gật khi đang lái." },
};

export const RATING_REASON_TEXT: Record<RatingReason, string> = {
  microsleep: "Có lúc nhắm mắt ngủ gật khi đang lái",
  frequent_alerts: "Nhiều lần được nhắc nhìn đường hoặc tập trung lái",
  tired_minutes: "Nhiều phút có dấu hiệu mệt",
  low_coverage: "Camera không thấy mặt trong một phần lớn chuyến đi, số liệu chưa đầy đủ",
};

/** "2 giờ 10 phút", "25 phút", "40 giây". */
export function formatDuration(seconds: number): string {
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s} giây`;
  const totalMin = Math.round(s / 60);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  if (h === 0) return `${m} phút`;
  return m ? `${h} giờ ${m} phút` : `${h} giờ`;
}

export function suggestionText(code: SuggestionCode, minutes?: number | null): string {
  const after = minutes != null ? formatDuration(minutes * 60) : "";
  switch (code) {
    case "rest_now":
      return "Hãy nghỉ ngơi thật sự trước khi lái tiếp.";
    case "rest_after":
      return `Lần sau nên dừng nghỉ sau khoảng ${after} lái.`;
    case "regular_breaks":
      return `Nghỉ khoảng 15 phút sau mỗi ${after} lái liên tục.`;
    case "phone_away":
      return "Để điện thoại xa tầm tay khi đang lái.";
    case "eyes_on_road":
      return "Giữ mắt nhìn đường; nhìn gương hay bảng đồng hồ thật ngắn.";
    case "check_camera":
      return "Chỉnh camera để luôn thấy rõ mặt bạn.";
    case "enroll":
      return "Lần sau, dừng xe vài giây để đăng ký khuôn mặt: nhận biết sẽ chính xác hơn.";
  }
}

const DROWSY_REASONS = ["microsleep", "unresponsive", "drowsy_score", "trend", "blink_rate"] as const;

function count(s: TripSummary, reasons: readonly string[]): number {
  return reasons.reduce((n, r) => n + (s.alerts_by_reason[r as keyof TripSummary["alerts_by_reason"]] ?? 0), 0);
}

/** The driver's one-paragraph story of the trip. */
export function driverStory(s: TripSummary): string {
  const parts: string[] = [];
  const rests = s.rests ? `, nghỉ ${s.rests} lần` : ", không nghỉ lần nào";
  const changes = s.driver_changes ? `, đổi tài ${s.driver_changes} lần` : "";
  parts.push(`Chuyến ${formatDuration(s.duration_s)}${rests}${changes}.`);
  if (s.first_tired_min != null) parts.push(`Bạn có dấu hiệu mệt từ phút lái thứ ${s.first_tired_min}.`);
  const nags = [
    [count(s, DROWSY_REASONS), "lần nhắc nghỉ"],
    [count(s, ["off_road"]), "lần nhắc nhìn đường"],
    [count(s, ["phone"]), "lần nhắc bỏ điện thoại"],
  ] as const;
  const said = nags.filter(([n]) => n > 0).map(([n, what]) => `${n} ${what}`);
  parts.push(said.length ? `Có ${said.join(", ")}.` : "Không có lần nhắc nào.");
  return parts.join(" ");
}

/** Phone time split by how the phone was held (M38, recorded only). "–" for summaries older than it. */
export function phoneKindText(s: TripSummary): string {
  if (s.phone_call_s == null || s.phone_text_s == null) return "–";
  const other = Math.max(0, s.phone_s - s.phone_call_s - s.phone_text_s);
  const parts = [`${Math.round(s.phone_call_s)} s gọi`, `${Math.round(s.phone_text_s)} s nhắn tin`];
  if (Math.round(other) > 0) parts.push(`${Math.round(other)} s không rõ`);
  return parts.join(" / ");
}

/** Glances away from the road (M38, measured only, never an alert). */
export function glanceText(s: TripSummary): string {
  if (s.glances == null || s.off_road_ratio_max == null) return "–";
  return `${s.glances} lần; lúc nhiều nhất ${Math.round(s.off_road_ratio_max * 100)}% thời gian của cửa sổ đo (chỉ đo, chưa cảnh báo)`;
}

export const DELIVERY_TEXT: Record<TripDelivery, string> = {
  sent: "Đã gửi bản tổng kết cho quản lý đội xe.",
  failed: "Chưa gửi được (mất kết nối). Bản tổng kết chỉ còn trên màn hình này.",
  local: "Chế độ dùng thử: bản tổng kết không được gửi đi.",
  device: "Thiết bị đã gửi bản tổng kết cho quản lý (mất mạng thì gửi khi có lại).",
};

export type Zone = "awake" | "tired" | "very_tired";

export function zoneOf(score: number, l1: number, l2: number): Zone {
  return score >= l2 ? "very_tired" : score >= l1 ? "tired" : "awake";
}

export const ZONE_TEXT: Record<Zone, string> = { awake: "Tỉnh táo", tired: "Hơi mệt", very_tired: "Mệt" };

// ------------------------------------------------------------------ redesigned summary screen (M58)

/** A suggestion as a tile of the design: a short value and what it is about. */
export function suggestionTile(code: SuggestionCode, minutes?: number | null): { value: string; label: string } {
  const after = minutes != null ? formatDuration(minutes * 60) : "";
  switch (code) {
    case "rest_now":
      return { value: "Nghỉ ngơi thật sự", label: "Trước khi lái tiếp" };
    case "rest_after":
      return { value: `Nghỉ sau ~${after}`, label: "Lần sau nên dừng nghỉ" };
    case "regular_breaks":
      return { value: `Nghỉ 15 phút mỗi ${after}`, label: "Khi lái liên tục" };
    case "phone_away":
      return { value: "Để điện thoại xa tầm tay", label: "Khi đang lái" };
    case "eyes_on_road":
      return { value: "Giữ mắt nhìn đường", label: "Nhìn gương, đồng hồ thật ngắn" };
    case "check_camera":
      return { value: "Chỉnh lại camera", label: "Để luôn thấy rõ mặt bạn" };
    case "enroll":
      return { value: "Đăng ký khuôn mặt", label: "Dừng xe vài giây ở lần sau" };
  }
}

export interface SummaryBar {
  score: number; // mean drowsy_score of the moving minutes of the bar (0 when all stopped)
  zone: Zone;
  stopped: boolean; // most of the bar's minutes the vehicle stood still
}

/** The whole trip in at most `maxBars` bars: `perBar` minutes each (1, 2, 3, ...), so a long trip still
 *  fits on one screen. Zones use this trip's thresholds. */
export function summaryBars(s: TripSummary, maxBars = 65): { perBar: number; bars: SummaryBar[] } {
  const perBar = Math.max(1, Math.ceil(s.minutes.length / maxBars));
  const bars: SummaryBar[] = [];
  for (let i = 0; i < s.minutes.length; i += perBar) {
    const group = s.minutes.slice(i, i + perBar);
    const moving = group.filter((m) => m.moving);
    const score = moving.length ? moving.reduce((a, m) => a + m.drowsy_score, 0) / moving.length : 0;
    bars.push({ score, zone: zoneOf(score, s.score_l1, s.score_l2), stopped: moving.length * 2 < group.length });
  }
  return { perBar, bars };
}
