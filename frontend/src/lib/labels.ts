// User-facing text (Vietnamese). Keys and code stay in English.
import type { Level, Reason, Role } from "./types";

export const LEVELS: Record<Level, { short: string; title: string; action: string; icon: string }> = {
  0: { short: "L0", title: "Bình thường", action: "Tỉnh táo, tiếp tục lái an toàn", icon: "✓" },
  1: { short: "L1", title: "Chú ý", action: "Biểu tượng + chuông nhẹ", icon: "!" },
  2: { short: "L2", title: "Cảnh báo", action: "Âm thanh + rung ghế", icon: "▲" },
  3: { short: "L3", title: "Nguy hiểm", action: "Hãy dừng xe nghỉ ngơi ngay", icon: "■" },
};

export const REASONS: Record<Reason, string> = {
  microsleep: "Nhắm mắt kéo dài",
  drowsy_score: "Dấu hiệu buồn ngủ",
  off_road: "Nhìn lệch khỏi đường",
  phone: "Dùng điện thoại",
  no_face: "Không thấy mặt tài xế",
  trend: "Mệt mỏi tăng dần",
  blink_rate: "Nhịp chớp mắt bất thường",
  camera_lost: "Mất camera: ngừng giám sát",
  camera_restored: "Camera hoạt động lại",
};

export const ROLES: Record<Role, string> = {
  admin: "Quản trị",
  engineer: "Kỹ sư",
  manager: "Quản lý đội xe",
  driver: "Tài xế",
};

export function reasonText(reason: string): string {
  return REASONS[reason as Reason] ?? reason;
}

// Threshold keys the backend lets engineers tune (backend/schemas.py THRESHOLD_SPECS).
export const THRESHOLD_GROUPS: { title: string; keys: { key: string; label: string; hint?: string }[] }[] = [
  {
    title: "Buồn ngủ",
    keys: [
      { key: "risk.microsleep_l3_s", label: "Nhắm mắt liên tục → L3", hint: "Giây mắt nhắm để báo L3 ngay" },
      { key: "risk.drowsy.l1", label: "drowsy_score → L1" },
      { key: "risk.drowsy.l2", label: "drowsy_score → L2", hint: "Phải lớn hơn ngưỡng L1" },
      { key: "drowsiness.microsleep_min_s", label: "Sự kiện microsleep từ", hint: "Góp điểm microsleep vào drowsy_score" },
      { key: "drowsiness.perclos_drowsy", label: "PERCLOS báo mệt" },
      { key: "drowsiness.yawn.min_s", label: "Thời gian ngáp tối thiểu" },
      { key: "drowsiness.nod.max_s", label: "Thời gian gục đầu tối đa" },
    ],
  },
  {
    title: "Mất tập trung",
    keys: [
      { key: "risk.distraction.off_road_s", label: "Nhìn lệch → L2" },
      { key: "risk.distraction.off_road_high_speed_s", label: "Nhìn lệch khi chạy nhanh → L2", hint: "Không lớn hơn ngưỡng thường" },
      { key: "risk.distraction.phone_ratio", label: "Tỉ lệ điện thoại trong 2 s → L2" },
      { key: "distraction.yaw_off_road_deg", label: "Góc quay đầu tính là nhìn lệch" },
    ],
  },
  {
    title: "Phát cảnh báo",
    keys: [
      { key: "alert.fall_hold_s", label: "Giữ mức trước khi hạ" },
      { key: "alert.cooldown_s.1", label: "Không lặp lại L1 trong" },
      { key: "alert.cooldown_s.2", label: "Không lặp lại L2 trong" },
      { key: "alert.cooldown_s.3", label: "Không lặp lại L3 trong" },
    ],
  },
];

export const UNITS: Record<string, string> = { s: "giây", score: "điểm", ratio: "tỉ lệ", deg: "độ" };

// HUD headline: what the driver should do (an action is read faster than a diagnosis).
export const REASON_ACTIONS: Record<Reason, string> = {
  microsleep: "Mở mắt! Dừng xe nghỉ ngay",
  drowsy_score: "Hãy tìm chỗ dừng nghỉ",
  trend: "Nên nghỉ ở trạm dừng tới",
  blink_rate: "Nên nghỉ ngơi sớm",
  off_road: "Nhìn về phía trước",
  phone: "Bỏ điện thoại xuống",
  no_face: "Ngồi đúng vị trí lái",
  camera_lost: "Kiểm tra camera",
  camera_restored: "Camera đã hoạt động lại",
};

// HUD screens when the driver is not being monitored (hud/hudModel.ts SystemState).
export const SYSTEM_TEXT: Record<"down" | "camera_lost" | "stale" | "connecting", { title: string; detail: string }> = {
  down: { title: "Không kết nối được thiết bị", detail: "HUD không nhận được trạng thái từ edge agent." },
  camera_lost: { title: "Mất camera", detail: "Hệ thống đang KHÔNG giám sát tài xế. Đang kết nối lại…" },
  stale: { title: "Không nhận dữ liệu từ camera", detail: "Vòng xử lý camera đã ngừng cập nhật." },
  connecting: { title: "Đang kết nối thiết bị…", detail: "Chờ khung hình đầu tiên từ camera." },
};
