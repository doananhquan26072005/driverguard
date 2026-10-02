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

const DROWSY_REASONS = ["microsleep", "drowsy_score", "trend", "blink_rate"] as const;

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
