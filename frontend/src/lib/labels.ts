// User-facing text (Vietnamese). Keys and code stay in English.
import type {
  DeletionRequest,
  EnrollHint,
  EnrollStep,
  EventTag,
  FleetDevice,
  FleetStatus,
  Level,
  MonitorState,
  PerfSnapshot,
  PerfStage,
  Reason,
  RefusalReason,
  Role,
  UnavailableCause,
} from "./types";

/** Milliseconds with at most one decimal, Vietnamese decimal comma. */
const ms = (v: number) => v.toLocaleString("vi-VN", { maximumFractionDigits: 1 });

export const LEVELS: Record<Level, { short: string; title: string; action: string; icon: string }> = {
  0: { short: "L0", title: "Bình thường", action: "Tỉnh táo, tiếp tục lái an toàn", icon: "✓" },
  1: { short: "L1", title: "Chú ý", action: "Bạn có vẻ mệt, nên nghỉ sớm", icon: "!" },
  2: { short: "L2", title: "Cảnh báo", action: "Tập trung lái xe", icon: "▲" },
  3: { short: "L3", title: "Nguy hiểm", action: "Dừng xe nghỉ ngay", icon: "■" },
};

export const REASONS: Record<Reason, string> = {
  microsleep: "Nhắm mắt kéo dài",
  drowsy_score: "Dấu hiệu buồn ngủ",
  off_road: "Rời mắt khỏi đường",
  phone: "Dùng điện thoại",
  no_face: "Không thấy mặt tài xế",
  trend: "Mệt mỏi tăng dần",
  blink_rate: "Nhịp chớp mắt bất thường",
  repeated_l1: "Đã nhắc nhiều lần",
  unresponsive: "Nhắm mắt không phản ứng với còi",
  repeated_l3: "Ngủ gật nhiều lần",
  no_answer: "Không trả lời “Bạn vẫn ổn chứ?”",
  config_applied: "Đã áp bộ ngưỡng mới",
  config_refused: "Từ chối bộ ngưỡng mới (không nhất quán, hoặc cần mở lại ứng dụng)",
  camera_lost: "Mất camera: ngừng giám sát",
  camera_restored: "Camera hoạt động lại",
  driver_enrolled: "Tài xế đã làm quen khuôn mặt",
  monitoring_unavailable: "Tạm ngưng giám sát",
  monitoring_restored: "Giám sát lại",
  driver_changed: "Đổi tài xế",
  vehicle_signal_lost: "Mất tín hiệu tốc độ xe",
  vehicle_signal_restored: "Có lại tín hiệu tốc độ xe",
  agent_error: "Lỗi xử lý: ngừng giám sát",
  agent_recovered: "Xử lý hoạt động lại",
  low_fps: "Máy xử lý chậm",
  fps_restored: "Tốc độ xử lý bình thường lại",
  phone_detection_lost: "Tạm chưa nhận biết được điện thoại",
  phone_detection_restored: "Nhận biết điện thoại hoạt động lại",
  road_pose_recalibrated: "Hiệu chuẩn lại hướng nhìn đường",
};

/** One or two words per alert reason, for the HUD's "Cảnh báo gần nhất" tile (M58). */
export const REASON_SHORT: Partial<Record<Reason, string>> = {
  microsleep: "Nhắm mắt",
  unresponsive: "Nhắm mắt",
  repeated_l3: "Ngủ gật",
  drowsy_score: "Buồn ngủ",
  trend: "Mệt tăng dần",
  blink_rate: "Chớp mắt",
  repeated_l1: "Nhắc nhiều lần",
  off_road: "Rời mắt",
  phone: "Điện thoại",
  no_face: "Không thấy mặt",
};

export const ROLES: Record<Role, string> = {
  admin: "Quản trị",
  engineer: "Kỹ sư",
  manager: "Quản lý đội xe",
  driver: "Tài xế",
};

/** A system event's reason with what its metrics add: "Tạm ngưng giám sát: camera bị che" (M43). */
export function eventReasonText(reason: string, metrics?: Record<string, unknown> | null): string {
  const cause = metrics?.cause;
  if (reason === "monitoring_unavailable" && typeof cause === "string" && cause in UNAVAILABLE_CAUSES)
    return `${reasonText(reason)}: ${UNAVAILABLE_CAUSES[cause as UnavailableCause].short}`;
  return reasonText(reason);
}

/** "mặt quá tối 40 s, camera bị che 12 s" for a trip summary, longest first; "" without any. */
export function unavailableCausesText(by?: Partial<Record<UnavailableCause, number>> | null): string {
  return Object.entries(by ?? {})
    .filter(([cause, s]) => cause in UNAVAILABLE_CAUSES && (s ?? 0) > 0)
    .sort((a, b) => (b[1] ?? 0) - (a[1] ?? 0))
    .map(([cause, s]) => `${UNAVAILABLE_CAUSES[cause as UnavailableCause].short} ${Math.round(s ?? 0)} s`)
    .join(", ");
}

export function reasonText(reason: string): string {
  return REASONS[reason as Reason] ?? reason;
}

// Fleet overview (M33): is the vehicle heard from, and what its last heartbeat said.
export const FLEET_STATUS: Record<FleetStatus, { title: string; badge: string }> = {
  online: { title: "Đang hoạt động", badge: "level-0" },
  offline: { title: "Mất liên lạc", badge: "level-3" },
  ended: { title: "Đã kết thúc ca lái", badge: "" },
  never: { title: "Chưa từng kết nối", badge: "" },
};

export const MONITOR_STATES: Record<MonitorState, string> = {
  monitoring: "Đang giám sát",
  unavailable: "Tạm ngưng giám sát",
  camera_lost: "Mất camera: không giám sát",
  stalled: "Không nhận khung hình: không giám sát",
  error: "Lỗi xử lý: không giám sát",
  ended: "Đã kết thúc ca lái",
};

/** What the vehicle is doing, in words. Offline: what it last said, marked as such. */
export function fleetStateText(d: Pick<FleetDevice, "status" | "state" | "moving">): string {
  if (d.status === "never" || d.status === "ended") return "–";
  if (d.state == null) return d.status === "online" ? "Không rõ (thiết bị không gửi trạng thái)" : "–";
  const motion = d.state === "monitoring" && d.moving != null ? (d.moving ? " · xe đang chạy" : " · xe đang đỗ") : "";
  const text = MONITOR_STATES[d.state] + motion;
  return d.status === "offline" ? `Lần cuối: ${text}` : text;
}

/** App and thresholds version of a vehicle, and whether it is behind (M41). */
export function fleetVersionText(d: Pick<FleetDevice, "versions" | "thresholds_current" | "thresholds_latest">): string {
  const v = d.versions;
  if (!v) return "–";
  const own = v.thresholds_version > 0 ? `ngưỡng v${v.thresholds_version}` : "ngưỡng gốc";
  let note = "";
  if (v.thresholds_ignored) note = " (bỏ qua bộ ngưỡng từ xa)";
  else if (d.thresholds_current === false) note = ` (mới nhất: v${d.thresholds_latest ?? "?"})`;
  return `app ${v.app} · ${own}${note}`;
}

/** "Đồng hồ thiết bị chậm 10 phút" for a vehicle whose clock the backend found wrong (M82); null: fine. */
export function clockSkewText(d: Pick<FleetDevice, "clock_skew_s" | "clock_wrong">): string | null {
  if (!d.clock_wrong || d.clock_skew_s == null) return null;
  const s = Math.abs(d.clock_skew_s);
  let size = `${Math.round(s)} giây`;
  if (s >= 2 * 86400) size = `${Math.round(s / 86400)} ngày`;
  else if (s >= 2 * 3600) size = `${Math.round(s / 3600)} giờ`;
  else if (s >= 120) size = `${Math.round(s / 60)} phút`;
  return `Đồng hồ thiết bị ${d.clock_skew_s > 0 ? "chậm" : "nhanh"} ${size}`;
}

const MODEL_NAMES: Record<string, string> = { landmarks: "khuôn mặt", eye_state: "mắt", phone: "điện thoại" };

/** Model fingerprints of a vehicle, for a tooltip. */
export function modelsText(v: FleetDevice["versions"]): string {
  const entries = Object.entries(v?.models ?? {});
  if (!entries.length) return "Thiết bị không gửi mã model";
  return entries.map(([name, hash]) => `Model ${MODEL_NAMES[name] ?? name}: ${hash}`).join("\n");
}

const PERF_STAGE_NAMES: Record<PerfStage, string> = {
  total: "Cả frame",
  camera_lag: "Từ lúc camera chụp tới lúc bắt đầu xử lý",
  capture: "Lấy ảnh từ camera",
  landmarks: "Model khuôn mặt",
  measure: "Đo độ sáng / độ nét",
  python: "Đặc trưng và quyết định",
  yolo_prep: "Chuẩn bị ảnh cho model điện thoại",
  yolo: "Model điện thoại (mỗi lần chạy)",
  yolo_age: "Tuổi kết quả điện thoại khi dùng",
};

/** How fast a vehicle's loop runs (M49), one line: "p95 23 ms". */
export function perfText(p: PerfSnapshot | null | undefined): string {
  const total = p?.stages_ms.total;
  return total ? `p95 ${ms(total.p95)} ms` : "–";
}

/** ... and every stage, for a tooltip. */
export function perfDetail(p: PerfSnapshot | null | undefined): string {
  if (!p) return "Thiết bị không gửi số đo tốc độ";
  const lines = (Object.keys(PERF_STAGE_NAMES) as PerfStage[])
    .filter((stage) => p.stages_ms[stage])
    .map((stage) => {
      const s = p.stages_ms[stage]!;
      return `${PERF_STAGE_NAMES[stage]}: p50 ${ms(s.p50)} · p95 ${ms(s.p95)} · max ${ms(s.max)} ms`;
    });
  if (p.landmarks_delegate) lines.push(`Model khuôn mặt chạy trên ${p.landmarks_delegate}`);
  if (p.gpu) lines.push(`WebGL: ${{ hardware: "GPU thật", software: "vẽ bằng phần mềm (không có GPU dùng được)", none: "không có" }[p.gpu]}`);
  if (p.yolo_provider === "webgpu") lines.push("Model điện thoại chạy trên GPU (WebGPU)");
  else if (p.yolo_threads) lines.push(`Model điện thoại: ${p.yolo_threads} luồng`);
  if (p.camera_delivered != null && p.camera_dropped != null)
    lines.push(`Frame camera bị bỏ: ${p.camera_dropped} / ${p.camera_delivered}`);
  return lines.join("\n");
}

/** Start-up of #/live (M67), one line for the same tooltip: seconds from "start" to each part being ready. */
export function startupText(s: { camera: number | null; python: number | null; face_model: number | null; phone_model: number | null; first_frame: number | null } | null | undefined): string {
  if (!s || s.first_frame == null) return "";
  const sec = (v: number | null) => (v == null ? "–" : (v / 1000).toFixed(1).replace(".", ","));
  return `Khởi động ${sec(s.first_frame)} s (camera ${sec(s.camera)} · Python ${sec(s.python)} · model mặt ${sec(s.face_model)} · model điện thoại ${sec(s.phone_model)})`;
}

/** What the loop of #/live did to keep getting frames (M71), for the camera card; "" when nothing. */
export function recoveryText(r: { pulls: number; reopens: number; yoloRestarts?: number } | null | undefined): string {
  if (!r || (!r.pulls && !r.reopens && !r.yoloRestarts)) return "";
  const parts = [];
  if (r.pulls) parts.push(`Vòng lặp đứng ${r.pulls} lần, đã tự chạy lại`);
  if (r.reopens) parts.push(`mở lại camera ${r.reopens} lần`);
  if (r.yoloRestarts) parts.push(`khởi động lại model điện thoại ${r.yoloRestarts} lần`);
  const text = parts.join(" · ");
  return text[0].toUpperCase() + text.slice(1);
}

/** ... and the short form for the camera card of #/live ("Chi tiết kỹ thuật"): p95 per stage, one line each. */
export function perfLines(p: PerfSnapshot): string {
  const s = p.stages_ms;
  const p95 = (stage: PerfStage) => (s[stage] ? ms(s[stage]!.p95) : "–");
  const lines = [
    `Frame p50 ${s.total ? ms(s.total.p50) : "–"} · p95 ${p95("total")} ms`,
    `Camera ${p95("capture")} · mặt ${p95("landmarks")}${p.landmarks_delegate ? ` (${p.landmarks_delegate})` : ""} · xử lý ${p95("python")} ms`,
  ];
  if (s.yolo) lines.push(`ĐT ${p95("yolo")} ms · tuổi ${p95("yolo_age")} ms · ${p.yolo_provider === "webgpu" ? "WebGPU" : `${p.yolo_threads ?? "?"} luồng`}`);
  if (p.camera_delivered != null && p.camera_dropped != null) lines.push(`Bỏ ${p.camera_dropped} / ${p.camera_delivered} frame`);
  return lines.join("\n");
}

export const EVENT_TAGS: Record<EventTag, { title: string; hint: string }> = {
  simulated: { title: "mô phỏng", hint: "Tốc độ / xi nhan lúc đó là tín hiệu mô phỏng, không phải xe thật" },
  forced: { title: "ép tay", hint: "Trạng thái do người bấm, không tính vào bất kỳ số liệu nào" },
};

// Deletion requests (M48): what the driver and the admin read.
export const DELETION_STATUS: Record<DeletionRequest["status"], string> = {
  pending: "Đang chờ quản trị xử lý",
  done: "Đã xoá",
  refused: "Bị từ chối",
};
export const REFUSAL_REASONS: Record<RefusalReason, string> = {
  legal_hold: "Dữ liệu phải giữ theo yêu cầu pháp lý",
  incident_open: "Đang có sự cố cần dữ liệu này để xem xét",
  duplicate: "Yêu cầu trùng",
  other: "Lý do khác (liên hệ quản trị)",
};

// Access log actions (backend/schemas.py AuditAction).
const AUDIT_ACTIONS: Record<string, string> = {
  read_events: "Xem nhật ký sự kiện",
  read_timeline: "Xem timeline mệt mỏi",
  read_trips: "Xem danh sách ca lái",
  read_stats: "Xem thống kê",
  read_fleet: "Xem đội xe",
  read_trip_reports: "Xem danh sách báo cáo ca lái",
  read_trip_report: "Xem một báo cáo ca lái",
  review_trip_report: "Đánh dấu đã xem báo cáo ca lái",
  read_access_log: "Xem nhật ký truy cập",
  update_thresholds: "Sửa ngưỡng",
  rollout_thresholds: "Áp phiên bản ngưỡng cho cả đội",
  create_user: "Tạo tài khoản",
  create_device: "Đăng ký thiết bị",
  purge_expired: "Xoá dữ liệu hết hạn",
  delete_driver_data: "Xoá dữ liệu của tài xế",
  refuse_deletion: "Từ chối yêu cầu xoá dữ liệu",
  delete_user: "Xoá tài khoản",
};

export function auditActionText(action: string): string {
  return AUDIT_ACTIONS[action] ?? action;
}

/** Whose data an access-log row is about, in words. */
export function auditScopeText(r: { driver_id: string | null; device_id: string | null; action: string }): string {
  if (r.driver_id) return r.device_id ? `Tài xế ${r.driver_id} (thiết bị ${r.device_id})` : `Tài xế ${r.driver_id}`;
  if (r.device_id) return `Thiết bị ${r.device_id}`;
  return r.action.startsWith("read_") ? "Cả đội xe" : "–";
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
      { key: "risk.distraction.off_road_s", label: "Rời mắt khỏi đường → L2" },
      { key: "risk.distraction.off_road_high_speed_s", label: "Rời mắt khi chạy nhanh → L2", hint: "Không lớn hơn ngưỡng thường" },
      { key: "risk.distraction.phone_ratio", label: "Tỉ lệ điện thoại trong 2 s → L2" },
      { key: "distraction.yaw_off_road_deg", label: "Góc quay đầu tính là rời mắt" },
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
  drowsy_score: "Tìm chỗ dừng nghỉ",
  trend: "Xong cuốc này nên nghỉ",
  blink_rate: "Nên nghỉ sớm",
  repeated_l1: "Bạn cần nghỉ rồi. Tìm chỗ dừng xe",
  unresponsive: "Tấp vào lề, dừng xe ngay!",
  repeated_l3: "Dừng xe nghỉ ngay",
  no_answer: "Chạm vào màn hình nếu bạn vẫn ổn",
  config_applied: "Đã cập nhật cài đặt cảnh báo",
  config_refused: "Giữ cài đặt cảnh báo cũ",
  off_road: "Nhìn đường!",
  phone: "Bỏ điện thoại xuống",
  no_face: "Camera chưa thấy rõ mặt bạn",
  camera_lost: "Kiểm tra camera",
  camera_restored: "Camera đã hoạt động lại",
  driver_enrolled: "Đã làm quen xong",
  monitoring_unavailable: "Camera chưa thấy rõ mặt bạn",
  monitoring_restored: "Đang theo dõi lại",
  driver_changed: "Người lái mới làm quen khuôn mặt",
  vehicle_signal_lost: "Kiểm tra kết nối tốc độ xe",
  vehicle_signal_restored: "Đã có lại tín hiệu tốc độ xe",
  agent_error: "Dừng xe an toàn nếu lỗi kéo dài",
  agent_recovered: "Đang theo dõi lại",
  low_fps: "Cảnh báo có thể đến trễ",
  fps_restored: "Đang theo dõi bình thường",
  phone_detection_lost: "Các cảnh báo khác vẫn hoạt động",
  phone_detection_restored: "Đang theo dõi bình thường",
  road_pose_recalibrated: "Đang theo dõi bình thường",
};

// Top bar chip while the device is too slow for a while (M28).
export const LOW_FPS_TEXT = "Máy chậm: cảnh báo có thể trễ";
// ... and while the phone detector gives no fresh results (M50): the other alerts still work.
export const PHONE_UNAVAILABLE_TEXT = "Tạm chưa nhận biết được điện thoại";

// Vehicle strip (HUD) while the vehicle link is lost (M26): while driving it is monitored as moving;
// while parked it stays parked until the speed comes back.
export const VEHICLE_SIGNAL_LOST_TEXT = {
  driving: "Mất tín hiệu tốc độ xe: vẫn theo dõi như đang chạy",
  parked: "Mất tín hiệu tốc độ xe: tạm coi như đang đỗ",
  never: "Chưa có tín hiệu tốc độ xe: đang theo dõi như xe đang chạy",
};

// Driver enrollment: what the HUD shows and says. Spoken too, since in steps 2 and 3 the
// driver is not looking at the screen.
export const ENROLL_STEPS: Record<EnrollStep, { title: string; detail: string }> = {
  look_camera: { title: "Nhìn thẳng vào camera", detail: "Mở mắt bình thường, ngậm miệng" },
  look_road: { title: "Nhìn ra đường phía trước", detail: "Như khi đang lái, giữ đầu yên" },
  close_eyes: { title: "Nhắm mắt lại", detail: "Mở mắt khi nghe tiếng bíp" },
};

export const ENROLL_HINTS: Record<EnrollHint, string> = {
  stop_vehicle: "Dừng xe để làm quen khuôn mặt",
  face_not_found: "Ngồi đúng vị trí, để cả khuôn mặt trong khung hình",
  too_dark: "Mặt quá tối hoặc chói. Bật đèn trần hoặc hạ tấm che nắng",
  look_camera: "Quay mặt về phía camera",
  look_road: "Nhìn ra đường phía trước như khi lái",
  hold_still: "Giữ đầu yên",
  open_eyes: "Mở mắt bình thường, nhìn thẳng",
  close_mouth: "Ngậm miệng lại",
  close_eyes: "Nhắm hẳn mắt lại",
};

export const ENROLL_TEXT = {
  title: "Làm quen khuôn mặt",
  done: "Làm quen xong",
  waiting: "Chưa làm quen khuôn mặt. Dừng xe để làm quen, cảnh báo sẽ chính xác hơn.",
  failed: "Chưa làm quen được. Bạn cứ lái, lần dừng xe sau sẽ thử lại.",
  later: "Chưa làm quen khuôn mặt. Sẽ hỏi lại ở lần dừng xe sau.",
};

// Shown before the steps: why the face is enrolled and what happens to the data. Must stay true to
// the code: enrollment.py keeps a few numbers in RAM for this trip only, publisher.py sends only
// "enrolled", how long it took and how many steps were redone, and no frame is ever stored or sent.
// Data policy (docs/data-policy.md): days the server keeps alert numbers / trip summaries before
// deleting them. Must equal the backend defaults (backend/settings.py retention_*_days); a Python
// test compares the two.
export const RETENTION_DAYS = { events: 60, summaries: 365 };

export const ENROLL_CONSENT = {
  title: "Làm quen khuôn mặt",
  headline: "Cho hệ thống làm quen với bạn",
  lead: "Mất khoảng 10 giây để hệ thống làm quen với khuôn mặt bạn, giúp cảnh báo chính xác hơn.",
  privacy: [
    "Không chụp, không lưu ảnh khuôn mặt. Hình ảnh camera chỉ được xử lý ngay trên thiết bị này.",
    "Chỉ ghi nhớ vài con số như độ mở mắt, miệng, tư thế đầu, và xoá khi kết thúc ca lái.",
    `Không gửi khuôn mặt hay các con số đó lên máy chủ. Số liệu cảnh báo tự xoá sau ${RETENTION_DAYS.events} ngày, bản tổng kết ca lái sau ${RETENTION_DAYS.summaries} ngày.`,
  ],
  agree: "Đồng ý, bắt đầu",
  later: "Để sau",
  laterNote: "Chưa làm quen vẫn lái được, nhưng cảnh báo có thể kém chính xác hơn.",
};

// Dashboard footer (data policy): what the numbers may be used for, and how long they are kept.
// days = 0: kept until deleted by hand.
export function policyNote(p: {
  retention_events_days: number;
  retention_summaries_days: number;
  retention_access_log_days?: number;
}): string {
  const keep = (days: number) => (days > 0 ? `tự xoá sau ${days} ngày` : "chưa đặt thời hạn xoá");
  return (
    "Cảnh báo có thể sai: không dùng một cảnh báo đơn lẻ để kỷ luật tài xế. " +
    `Số liệu cảnh báo ${keep(p.retention_events_days)}, bản tổng kết ca lái ${keep(p.retention_summaries_days)}. ` +
    "Không có ảnh hay video khuôn mặt nào được lưu." +
    (p.retention_access_log_days != null ? ` Mỗi lần xem dữ liệu tài xế đều được ghi vào nhật ký truy cập (${keep(p.retention_access_log_days)}).` : "")
  );
}

// Why monitoring is unavailable (M43): the HUD tells the driver what to fix, the dashboard what happened.
export const UNAVAILABLE_CAUSES: Record<UnavailableCause, { short: string; detail: string }> = {
  no_face: { short: "không thấy mặt", detail: "Camera chưa thấy mặt bạn. Ngồi đúng vị trí lái, không che camera." },
  camera_blocked: { short: "camera bị che", detail: "Camera bị che hoặc quá tối. Khi dừng xe, kiểm tra ống kính camera." },
  bad_angle: { short: "camera lệch", detail: "Khuôn mặt nằm ngoài khung hình. Khi dừng xe, chỉnh camera hướng vào mặt." },
  low_light: { short: "mặt quá tối", detail: "Khuôn mặt quá tối, không thấy rõ mắt. Bật đèn trần, hoặc chỉnh camera khi dừng xe." },
  glare: { short: "mặt bị chói", detail: "Khuôn mặt bị chói nắng, không thấy rõ mắt. Hạ tấm che nắng, hoặc chỉnh camera khi dừng xe." },
  blur: { short: "ảnh mờ", detail: "Ảnh camera bị mờ, không thấy rõ mắt. Khi dừng xe, lau ống kính camera." },
  slow_loop: { short: "máy xử lý quá chậm", detail: "Máy đang quá chậm nên chưa theo dõi được. Khi dừng xe, hãy khởi động lại thiết bị." },
};

// "Bạn vẫn ổn chứ?" (M44): the whole screen is one button, so it can be hit without aiming.
export const PRESENCE_TEXT = {
  title: "Bạn vẫn ổn chứ?",
  tap: "Chạm vào màn hình",
  detail: "Camera không thấy bạn. Chạm bất kỳ đâu nếu bạn vẫn ổn.",
  unanswered: "Bạn chưa phản hồi nên hệ thống đã báo quản lý đội xe.",
};

// Shown while the browser still blocks sound (hud/chime.ts armAudio): one touch turns it on.
export const SOUND_BLOCKED_TEXT = "Âm thanh cảnh báo chưa bật. Chạm vào màn hình để bật.";

// HUD screens when the driver is not being monitored (hud/hudModel.ts SystemState).
export const SYSTEM_TEXT: Record<
  "down" | "camera_lost" | "error" | "unavailable" | "stale" | "connecting",
  { title: string; detail: string }
> = {
  error: { title: "Hệ thống gặp lỗi", detail: "Hiện chưa theo dõi được bạn. Đang tự thử lại…" },
  unavailable: {
    title: "Tạm ngưng theo dõi",
    detail: "Camera chưa thấy mặt bạn. Ngồi đúng vị trí lái, không che camera.",
  },
  down: { title: "Mất kết nối với thiết bị", detail: "Hiện chưa cảnh báo được. Khi dừng xe, kiểm tra nguồn và cáp." },
  camera_lost: { title: "Mất hình camera", detail: "Hiện chưa theo dõi được bạn. Đang kết nối lại…" },
  stale: { title: "Camera bị đứng hình", detail: "Hiện chưa theo dõi được bạn. Đang tự thử lại…" },
  connecting: { title: "Đang khởi động…", detail: "Sẵn sàng sau vài giây." },
};
