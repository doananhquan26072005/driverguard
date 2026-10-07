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
  repeated_l1: "Đã nhắc nhiều lần",
  unresponsive: "Nhắm mắt không phản ứng với còi",
  repeated_l3: "Ngủ gật nhiều lần",
  no_answer: "Không trả lời “Bạn còn ở đó không?”",
  config_applied: "Đã áp bộ ngưỡng mới",
  config_refused: "Từ chối bộ ngưỡng mới (không nhất quán)",
  camera_lost: "Mất camera: ngừng giám sát",
  camera_restored: "Camera hoạt động lại",
  driver_enrolled: "Đã đăng ký tài xế",
  monitoring_unavailable: "Tạm ngưng giám sát",
  monitoring_restored: "Giám sát lại",
  driver_changed: "Đổi tài xế",
  vehicle_signal_lost: "Mất tín hiệu xe",
  vehicle_signal_restored: "Có lại tín hiệu xe",
  agent_error: "Lỗi xử lý: ngừng giám sát",
  agent_recovered: "Xử lý hoạt động lại",
  low_fps: "Máy xử lý chậm",
  fps_restored: "Tốc độ xử lý bình thường lại",
  phone_detection_lost: "Không phát hiện được điện thoại",
  phone_detection_restored: "Phát hiện điện thoại hoạt động lại",
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
  ended: { title: "Đã kết thúc chuyến", badge: "" },
  never: { title: "Chưa từng kết nối", badge: "" },
};

export const MONITOR_STATES: Record<MonitorState, string> = {
  monitoring: "Đang giám sát",
  unavailable: "Tạm ngưng giám sát",
  camera_lost: "Mất camera: không giám sát",
  stalled: "Không nhận khung hình: không giám sát",
  error: "Lỗi xử lý: không giám sát",
  ended: "Đã kết thúc chuyến",
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
  if (p.yolo_threads) lines.push(`Model điện thoại: ${p.yolo_threads} luồng`);
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

/** ... and the short form for the camera card of #/live ("Chi tiết kỹ thuật"): p95 per stage, one line each. */
export function perfLines(p: PerfSnapshot): string {
  const s = p.stages_ms;
  const p95 = (stage: PerfStage) => (s[stage] ? ms(s[stage]!.p95) : "–");
  const lines = [
    `Frame p50 ${s.total ? ms(s.total.p50) : "–"} · p95 ${p95("total")} ms`,
    `Camera ${p95("capture")} · mặt ${p95("landmarks")}${p.landmarks_delegate ? ` (${p.landmarks_delegate})` : ""} · xử lý ${p95("python")} ms`,
  ];
  if (s.yolo) lines.push(`ĐT ${p95("yolo")} ms · tuổi ${p95("yolo_age")} ms · ${p.yolo_threads ?? "?"} luồng`);
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
  read_trips: "Xem danh sách chuyến",
  read_stats: "Xem thống kê",
  read_fleet: "Xem đội xe",
  read_trip_reports: "Xem danh sách báo cáo chuyến",
  read_trip_report: "Xem một báo cáo chuyến",
  review_trip_report: "Đánh dấu đã xem báo cáo chuyến",
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
  repeated_l1: "Đã nhắc nhiều lần: hãy dừng nghỉ",
  unresponsive: "DỪNG XE NGAY!",
  repeated_l3: "Ngủ gật nhiều lần: dừng xe nghỉ ngay",
  no_answer: "Chạm vào màn hình nếu bạn vẫn ổn",
  config_applied: "Đã cập nhật ngưỡng cảnh báo",
  config_refused: "Giữ ngưỡng cảnh báo cũ",
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
  phone_detection_lost: "Các cảnh báo khác vẫn hoạt động",
  phone_detection_restored: "Đang giám sát bình thường",
};

// Top bar chip while the device is too slow for a while (M28).
export const LOW_FPS_TEXT = "Máy chậm: cảnh báo có thể trễ";
// ... and while the phone detector gives no fresh results (M50): the other alerts still work.
export const PHONE_UNAVAILABLE_TEXT = "Không phát hiện được điện thoại";

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
// Data policy (docs/data-policy.md): days the server keeps alert numbers / trip summaries before
// deleting them. Must equal the backend defaults (backend/settings.py retention_*_days); a Python
// test compares the two.
export const RETENTION_DAYS = { events: 60, summaries: 365 };

export const ENROLL_CONSENT = {
  title: "Đăng ký khuôn mặt",
  lead: "Để nhận biết buồn ngủ và mất tập trung chính xác nhất, hệ thống cần làm quen với khuôn mặt của bạn. Mất khoảng 10 giây, khi xe đang dừng.",
  privacy: [
    "Không chụp, không lưu ảnh khuôn mặt. Hình ảnh camera chỉ được xử lý ngay trên thiết bị này.",
    "Chỉ ghi nhớ vài con số như độ mở mắt, miệng, tư thế đầu, và xoá khi kết thúc chuyến.",
    `Không gửi khuôn mặt hay các con số đó lên máy chủ. Số liệu cảnh báo tự xoá sau ${RETENTION_DAYS.events} ngày, bản tổng kết chuyến sau ${RETENTION_DAYS.summaries} ngày.`,
  ],
  agree: "Đồng ý, bắt đầu đăng ký",
  later: "Để sau",
  laterNote: "Chưa đăng ký vẫn được lái, nhưng nhận biết kém chính xác hơn.",
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
    `Số liệu cảnh báo ${keep(p.retention_events_days)}, bản tổng kết chuyến ${keep(p.retention_summaries_days)}. ` +
    "Không có ảnh hay video khuôn mặt nào được lưu." +
    (p.retention_access_log_days != null ? ` Mỗi lần xem dữ liệu tài xế đều được ghi vào nhật ký truy cập (${keep(p.retention_access_log_days)}).` : "")
  );
}

// Why monitoring is unavailable (M43): the HUD tells the driver what to fix, the dashboard what happened.
export const UNAVAILABLE_CAUSES: Record<UnavailableCause, { short: string; detail: string }> = {
  no_face: { short: "không thấy mặt", detail: "Không thấy mặt tài xế. Ngồi đúng vị trí lái, không che camera." },
  camera_blocked: { short: "camera bị che", detail: "Camera bị che hoặc quá tối. Kiểm tra ống kính camera." },
  bad_angle: { short: "camera lệch", detail: "Khuôn mặt nằm ngoài khung hình. Chỉnh camera hướng vào mặt." },
  low_light: { short: "mặt quá tối", detail: "Khuôn mặt quá tối, không đọc được mắt. Bật đèn trần hoặc chỉnh camera." },
  glare: { short: "mặt bị chói", detail: "Khuôn mặt bị chói nắng, không đọc được mắt. Hạ tấm che nắng hoặc chỉnh camera." },
  blur: { short: "ảnh mờ", detail: "Ảnh camera bị mờ, không đọc được mắt. Lau ống kính camera." },
};

// "Bạn còn ở đó không?" (M44): the whole screen is one button, so it can be hit without aiming.
export const PRESENCE_TEXT = {
  title: "Bạn còn ở đó không?",
  tap: "Chạm vào màn hình",
  detail: "Camera không thấy bạn. Chạm bất kỳ đâu nếu bạn vẫn ổn.",
  unanswered: "Chưa có trả lời: đã báo cho quản lý đội xe.",
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
