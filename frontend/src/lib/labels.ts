// User-facing text (Vietnamese). Keys and code stay in English.
import type { EnrollHint, EnrollStep, Level, Reason, Role } from "./types";

export const LEVELS: Record<Level, { short: string; title: string; action: string; icon: string }> = {
  0: { short: "L0", title: "Bình thường", action: "Tỉnh táo, tiếp tục lái an toàn", icon: "✓" },
  1: { short: "L1", title: "Chú ý", action: "Bạn có vẻ mệt, nên nghỉ sớm", icon: "!" },
  2: { short: "L2", title: "Cảnh báo", action: "Tập trung lái xe ngay", icon: "▲" },
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
  driver_enrolled: "Đã đăng ký tài xế",
  monitoring_unavailable: "Tạm ngưng giám sát: không thấy mặt",
  monitoring_restored: "Giám sát lại",
  driver_changed: "Đổi tài xế",
  vehicle_signal_lost: "Mất tín hiệu xe",
  vehicle_signal_restored: "Có lại tín hiệu xe",
  agent_error: "Lỗi xử lý: ngừng giám sát",
  agent_recovered: "Xử lý hoạt động lại",
  low_fps: "Máy xử lý chậm",
  fps_restored: "Tốc độ xử lý bình thường lại",
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
      { key: "distraction.turn_signal_extra_yaw_deg", label: "Góc nới thêm về phía bật xi nhan", hint: "Chỉ phía xi nhan, phía kia giữ nguyên" },
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
  driver_enrolled: "Đã đăng ký tài xế",
  monitoring_unavailable: "Ngồi đúng vị trí lái",
  monitoring_restored: "Đang giám sát lại",
  driver_changed: "Người lái mới đăng ký khuôn mặt",
  vehicle_signal_lost: "Kiểm tra kết nối tốc độ xe",
  vehicle_signal_restored: "Đã có lại tín hiệu xe",
  agent_error: "Dừng xe an toàn nếu lỗi kéo dài",
  agent_recovered: "Đang giám sát lại",
  low_fps: "Cảnh báo có thể đến trễ",
  fps_restored: "Đang giám sát bình thường",
};

// Top bar chip while the device is too slow for a while (M28).
export const LOW_FPS_TEXT = "Máy chậm: cảnh báo có thể trễ";

// Vehicle strip (HUD) while the vehicle link is lost (M26): while driving it is monitored as moving;
// while parked it stays parked until the speed comes back.
export const VEHICLE_SIGNAL_LOST_TEXT = {
  driving: "Mất tín hiệu xe: vẫn giám sát như đang chạy",
  parked: "Mất tín hiệu xe: coi như đang đỗ đến khi có lại tốc độ",
};

// Driver enrollment: what the HUD shows and says. Spoken too, since in steps 2 and 3 the
// driver is not looking at the screen.
export const ENROLL_STEPS: Record<EnrollStep, { title: string; detail: string }> = {
  look_camera: { title: "Nhìn thẳng vào camera", detail: "Mở mắt bình thường, ngậm miệng" },
  look_road: { title: "Nhìn ra đường phía trước", detail: "Như khi đang lái, giữ đầu yên" },
  close_eyes: { title: "Nhắm mắt lại", detail: "Mở mắt khi nghe tiếng bíp" },
};

export const ENROLL_HINTS: Record<EnrollHint, string> = {
  stop_vehicle: "Dừng xe để đăng ký tài xế",
  face_not_found: "Ngồi đúng vị trí, để cả khuôn mặt trong khung hình",
  too_dark: "Hơi tối hoặc chói, bật đèn trong xe",
  look_camera: "Quay mặt về phía camera",
  look_road: "Nhìn ra đường phía trước như khi lái",
  hold_still: "Giữ đầu yên",
  open_eyes: "Mở mắt bình thường, nhìn thẳng",
  close_mouth: "Ngậm miệng lại",
  close_eyes: "Nhắm hẳn mắt lại",
};

export const ENROLL_TEXT = {
  title: "Đăng ký tài xế",
  done: "Đăng ký xong",
  waiting: "Chưa đăng ký tài xế. Dừng xe để đăng ký, nhận diện sẽ chính xác hơn.",
  failed: "Chưa đăng ký được. Sẽ thử lại ở lần dừng xe sau.",
  later: "Chưa đăng ký tài xế. Sẽ hỏi lại ở lần dừng xe sau.",
};

// Shown before the steps: why the face is enrolled and what happens to the data. Must stay true to
// the code: enrollment.py keeps a few numbers in RAM for this trip only, publisher.py sends only
// "enrolled", how long it took and how many steps were redone, and no frame is ever stored or sent.
export const ENROLL_CONSENT = {
  title: "Đăng ký khuôn mặt",
  lead: "Để nhận biết buồn ngủ và mất tập trung chính xác nhất, hệ thống cần làm quen với khuôn mặt của bạn. Mất khoảng 10 giây, khi xe đang dừng.",
  privacy: [
    "Không chụp, không lưu ảnh khuôn mặt. Hình ảnh camera chỉ được xử lý ngay trên thiết bị này.",
    "Chỉ ghi nhớ vài con số như độ mở mắt, miệng, tư thế đầu, và xoá khi kết thúc chuyến.",
    "Không gửi khuôn mặt hay các con số đó lên máy chủ. Quản lý chỉ biết bạn đã đăng ký.",
  ],
  agree: "Đồng ý, bắt đầu đăng ký",
  later: "Để sau",
  laterNote: "Chưa đăng ký vẫn được lái, nhưng nhận biết kém chính xác hơn.",
};

// Shown while the browser still blocks sound (hud/chime.ts armAudio): one touch turns it on.
export const SOUND_BLOCKED_TEXT = "Âm thanh cảnh báo chưa bật. Chạm vào màn hình để bật.";

// HUD screens when the driver is not being monitored (hud/hudModel.ts SystemState).
export const SYSTEM_TEXT: Record<
  "down" | "camera_lost" | "error" | "unavailable" | "stale" | "connecting",
  { title: string; detail: string }
> = {
  error: { title: "Lỗi xử lý", detail: "Hệ thống đang KHÔNG giám sát tài xế. Đang thử lại…" },
  unavailable: {
    title: "Tạm ngưng giám sát",
    detail: "Không thấy mặt tài xế. Ngồi đúng vị trí lái, không che camera.",
  },
  down: { title: "Không kết nối được thiết bị", detail: "HUD không nhận được trạng thái từ edge agent." },
  camera_lost: { title: "Mất camera", detail: "Hệ thống đang KHÔNG giám sát tài xế. Đang kết nối lại…" },
  stale: { title: "Không nhận dữ liệu từ camera", detail: "Vòng xử lý camera đã ngừng cập nhật." },
  connecting: { title: "Đang kết nối thiết bị…", detail: "Chờ khung hình đầu tiên từ camera." },
};
