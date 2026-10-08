import { describe, expect, it } from "vitest";
import { ALARM_REPEAT_S, alertSound, armAudio, play, systemSound } from "../hud/chime";
import { DEMO_CYCLE_S, demoSnapshot, DEMO_SCRIPT } from "../hud/demo";
import { ago, changedValues, clockText, dayKey, dayRange, formatPercent, query, rangeStart } from "./format";
import {
  auditActionText,
  auditScopeText,
  ENROLL_CONSENT,
  EVENT_TAGS,
  fleetStateText,
  fleetVersionText,
  modelsText,
  perfDetail,
  perfLines,
  perfText,
  recoveryText,
  startupText,
  policyNote,
  eventReasonText,
  reasonText,
  unavailableCausesText,
  REASON_ACTIONS,
  RETENTION_DAYS,
} from "./labels";
import { fleetCounts, newUrgentIds, sortFleet, urgentDevices } from "../dashboard/FleetView";
import { parseDeviceList } from "../dashboard/ThresholdsView";
import { deletionStatusText, exportFileName } from "../dashboard/MyDataCard";
import { primaryReason } from "../hud/hudModel";
import type { FleetDevice } from "./types";
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

describe("fleet overview (M33)", () => {
  const device = (over: Partial<FleetDevice>): FleetDevice => ({
    device_id: "cam-001",
    driver_id: "drv-001",
    status: "online",
    state: "monitoring",
    moving: true,
    trip_id: "trip-1",
    last_seen: "2026-10-05T08:00:00Z",
    alerts_by_level: { "1": 0, "2": 0, "3": 0 },
    last_event: null,
    ...over,
  });

  it("turns a local day into its start and the next midnight", () => {
    const r = dayRange("2026-10-05")!;
    expect(new Date(r.since).getHours()).toBe(0);
    expect(Date.parse(r.until) - Date.parse(r.since)).toBe(24 * 3600_000);
    expect(dayKey(new Date(r.since))).toBe("2026-10-05");
    expect(dayRange("hôm nay")).toBeNull();
  });

  it("lists vehicles that need attention now first, newest event first, and rings once per event (M44)", () => {
    const urgent = (ts: string, id: string | null) => ({ ts, type: "drowsiness" as const, level: 3 as const, reasons: ["unresponsive" as const], event_id: id });
    const list = [
      device({ device_id: "a" }),
      device({ device_id: "b", status: "offline" }),
      device({ device_id: "c", urgent: urgent("2026-10-06T08:00:00Z", "e1") }),
      device({ device_id: "d", urgent: urgent("2026-10-06T08:01:00Z", null) }),
    ];
    expect(sortFleet(list).map((d) => d.device_id)).toEqual(["c", "d", "b", "a"]);
    expect(urgentDevices(list).map((d) => d.device_id)).toEqual(["d", "c"]);
    expect(fleetCounts(list).urgent).toBe(2);
    expect(newUrgentIds(list, new Set())).toEqual(["d:2026-10-06T08:01:00Z", "e1"]);
    expect(newUrgentIds(list, new Set(["e1", "d:2026-10-06T08:01:00Z"]))).toEqual([]);
    expect(reasonText("unresponsive")).toBe("Nhắm mắt không phản ứng với còi");
    expect(reasonText("no_answer")).toContain("Bạn còn ở đó không?");
  });

  it("names a driver's export file and says what happened to a deletion request (M48)", () => {
    expect(exportFileName("drv-001", new Date("2026-10-06T03:00:00Z"))).toBe("driverguard-drv-001-2026-10-06.json");
    expect(exportFileName("../x y", new Date("2026-10-06T03:00:00Z"))).toBe("driverguard-.._x_y-2026-10-06.json");
    const req = { id: 1, driver_id: "drv-001", requested_by: "an", requested_at: "2026-10-06T03:00:00Z", handled_by: null, handled_at: null };
    expect(deletionStatusText({ ...req, status: "pending", reason: null })).toBe("Đang chờ quản trị xử lý");
    expect(deletionStatusText({ ...req, status: "refused", reason: "incident_open" })).toContain("Đang có sự cố");
    expect(deletionStatusText({ ...req, status: "done", reason: null })).toBe("Đã xoá");
    expect(auditActionText("refuse_deletion")).toBe("Từ chối yêu cầu xoá dữ liệu");
  });

  it("reads the trial devices an engineer typed (M47)", () => {
    expect(parseDeviceList(" cam-001, cam-007;web-an  cam-001 ")).toEqual(["cam-001", "cam-007", "web-an"]);
    expect(parseDeviceList("  ")).toEqual([]);
    expect(reasonText("config_applied")).toBe("Đã áp bộ ngưỡng mới");
    expect(auditActionText("rollout_thresholds")).toBe("Áp phiên bản ngưỡng cho cả đội");
  });

  it("names why monitoring is unavailable (M43)", () => {
    expect(eventReasonText("monitoring_unavailable", { cause: "camera_blocked" })).toBe("Tạm ngưng giám sát: camera bị che");
    expect(eventReasonText("monitoring_unavailable", {})).toBe("Tạm ngưng giám sát");
    expect(eventReasonText("monitoring_unavailable", { cause: "made_up" })).toBe("Tạm ngưng giám sát");
    expect(eventReasonText("phone", { cause: "glare" })).toBe("Dùng điện thoại");
    expect(unavailableCausesText({ low_light: 40.2, camera_blocked: 12, glare: 0 })).toBe("mặt quá tối 40 s, camera bị che 12 s");
    expect(unavailableCausesText(undefined)).toBe("");
  });

  it("says what the vehicle is doing in words, never a raw code", () => {
    expect(fleetStateText(device({}))).toBe("Đang giám sát · xe đang chạy");
    expect(fleetStateText(device({ moving: false }))).toBe("Đang giám sát · xe đang đỗ");
    expect(fleetStateText(device({ moving: null }))).toBe("Đang giám sát");
    expect(fleetStateText(device({ state: "camera_lost" }))).toBe("Mất camera: không giám sát");
    expect(fleetStateText(device({ status: "offline" }))).toBe("Lần cuối: Đang giám sát · xe đang chạy");
    expect(fleetStateText(device({ status: "ended", state: "ended" }))).toBe("–");
    expect(fleetStateText(device({ state: null }))).toContain("Không rõ");
  });

  it("lists lost vehicles first and counts by status", () => {
    const list = [
      device({ device_id: "b", status: "ended" }),
      device({ device_id: "c", status: "online", alerts_by_level: { "1": 1, "2": 2, "3": 0 } }),
      device({ device_id: "a", status: "offline", alerts_by_level: { "1": 0, "2": 0, "3": 1 } }),
      device({ device_id: "d", status: "never" }),
    ];
    expect(sortFleet(list).map((d) => d.device_id)).toEqual(["a", "c", "b", "d"]);
    expect(fleetCounts(list)).toEqual({ total: 4, online: 1, offline: 1, alerts: 4, urgent: 0 });
  });
});

describe("repeated L1 raised as L2 (M32)", () => {
  it("has its own words and leads the HUD headline", () => {
    expect(reasonText("repeated_l1")).toBe("Đã nhắc nhiều lần");
    expect(primaryReason(["drowsy_score", "repeated_l1"])).toBe("repeated_l1");
    expect(REASON_ACTIONS.repeated_l1).toContain("dừng nghỉ");
    expect(primaryReason(["microsleep", "repeated_l1"])).toBe("microsleep");
  });
});

describe("data policy texts (M37)", () => {
  it("tells the driver how long the numbers are kept, before enrolling", () => {
    const line = ENROLL_CONSENT.privacy.join(" ");
    expect(line).toContain(`${RETENTION_DAYS.events} ngày`);
    expect(line).toContain(`${RETENTION_DAYS.summaries} ngày`);
    expect(ENROLL_CONSENT.privacy).toHaveLength(3); // no extra line: the screen is already tight at 1024x600
  });

  it("reminds the dashboard reader what one alert may not be used for", () => {
    const note = policyNote({ retention_events_days: 60, retention_summaries_days: 365 });
    expect(note).toContain("không dùng một cảnh báo đơn lẻ để kỷ luật");
    expect(note).toContain("tự xoá sau 60 ngày");
    expect(note).toContain("tự xoá sau 365 ngày");
    expect(policyNote({ retention_events_days: 0, retention_summaries_days: 365 })).toContain("chưa đặt thời hạn xoá");
  });
});

describe("loop timings (M49)", () => {
  const perf = {
    samples: 300,
    stages_ms: {
      capture: { p50: 1.2, p95: 2, max: 9 },
      landmarks: { p50: 8, p95: 11.5, max: 30 },
      python: { p50: 0.6, p95: 0.9, max: 4 },
      total: { p50: 10.5, p95: 14, max: 41 },
      yolo: { p50: 166, p95: 170, max: 181 },
      yolo_age: { p50: 250, p95: 340, max: 380 },
    },
    landmarks_delegate: "GPU" as const,
    yolo_threads: 1,
    camera_delivered: 303,
    camera_dropped: 3,
  };

  it("one number in the fleet table, every stage in its tooltip", () => {
    expect(perfText(null)).toBe("–");
    expect(perfText(perf)).toBe("p95 14 ms");
    expect(perfDetail(null)).toBe("Thiết bị không gửi số đo tốc độ");
    const detail = perfDetail(perf).split("\n");
    expect(detail[0]).toBe("Cả frame: p50 10,5 · p95 14 · max 41 ms");
    expect(detail).toContain("Model khuôn mặt chạy trên GPU");
    expect(perfDetail({ ...perf, landmarks_delegate: "CPU", gpu: "software" })).toContain("WebGL: vẽ bằng phần mềm (không có GPU dùng được)");
    expect(detail).toContain("Model điện thoại: 1 luồng");
    expect(detail).toContain("Frame camera bị bỏ: 3 / 303");
  });

  it("short lines for the camera card of #/live", () => {
    expect(perfLines(perf).split("\n")).toEqual([
      "Frame p50 10,5 · p95 14 ms",
      "Camera 2 · mặt 11,5 (GPU) · xử lý 0,9 ms",
      "ĐT 170 ms · tuổi 340 ms · 1 luồng",
      "Bỏ 3 / 303 frame",
    ]);
    const bare = { ...perf, stages_ms: { total: perf.stages_ms.total }, landmarks_delegate: null, camera_delivered: null, camera_dropped: null };
    expect(perfLines(bare).split("\n")).toEqual(["Frame p50 10,5 · p95 14 ms", "Camera – · mặt – · xử lý – ms"]);
  });

  it("says when the phone model runs on WebGPU instead of counting threads (M67)", () => {
    const onGpu = { ...perf, yolo_provider: "webgpu" as const };
    expect(perfDetail(onGpu)).toContain("Model điện thoại chạy trên GPU (WebGPU)");
    expect(perfDetail(onGpu)).not.toContain("luồng");
    expect(perfLines(onGpu).split("\n")[2]).toBe("ĐT 170 ms · tuổi 340 ms · WebGPU");
    expect(perfDetail({ ...perf, yolo_provider: "wasm" as const })).toContain("Model điện thoại: 1 luồng");
  });

  it("one line for the start-up, nothing before the first frame (M67)", () => {
    const startup = { camera: 120, python: 1180, face_model: 1310, phone_model: 2040, first_frame: 1340 };
    expect(startupText(startup)).toBe("Khởi động 1,3 s (camera 0,1 · Python 1,2 · model mặt 1,3 · model điện thoại 2,0)");
    expect(startupText({ ...startup, phone_model: null })).toContain("model điện thoại –");
    expect(startupText({ ...startup, first_frame: null })).toBe("");
    expect(startupText(null)).toBe("");
  });

  it("says what the loop of #/live did to keep getting frames (M71), and nothing when it did nothing", () => {
    expect(recoveryText({ pulls: 0, reopens: 0 })).toBe("");
    expect(recoveryText(null)).toBe("");
    expect(recoveryText({ pulls: 2, reopens: 0 })).toBe("Vòng lặp đứng 2 lần, đã tự chạy lại");
    expect(recoveryText({ pulls: 0, reopens: 3 })).toBe("Mở lại camera 3 lần");
    expect(recoveryText({ pulls: 1, reopens: 1 })).toBe("Vòng lặp đứng 1 lần, đã tự chạy lại · mở lại camera 1 lần");
  });
});

describe("versions, tags and the access log (M41)", () => {
  const versions = { app: "3.0.0", thresholds_version: 2, thresholds_ignored: false, models: { phone: "0123456789ab" } };

  it("says what a vehicle runs and when it is behind", () => {
    expect(fleetVersionText({ versions: null })).toBe("–");
    expect(fleetVersionText({ versions, thresholds_current: true, thresholds_latest: 2 })).toBe("app 3.0.0 · ngưỡng v2");
    expect(fleetVersionText({ versions, thresholds_current: false, thresholds_latest: 3 })).toBe(
      "app 3.0.0 · ngưỡng v2 (mới nhất: v3)",
    );
    const local = { ...versions, thresholds_version: 0 };
    expect(fleetVersionText({ versions: local, thresholds_current: true, thresholds_latest: 0 })).toBe("app 3.0.0 · ngưỡng gốc");
    const refused = { ...local, thresholds_ignored: true };
    expect(fleetVersionText({ versions: refused, thresholds_current: false, thresholds_latest: 3 })).toContain("bỏ qua bộ ngưỡng từ xa");
  });

  it("lists model fingerprints in words", () => {
    expect(modelsText(versions)).toBe("Model điện thoại: 0123456789ab");
    expect(modelsText(null)).toBe("Thiết bị không gửi mã model");
  });

  it("has words for both event tags", () => {
    expect(EVENT_TAGS.simulated.title).toBe("mô phỏng");
    expect(EVENT_TAGS.forced.hint).toContain("không tính vào bất kỳ số liệu nào");
  });

  it("puts access-log rows in words", () => {
    expect(auditActionText("read_events")).toBe("Xem nhật ký sự kiện");
    expect(auditActionText("something_new")).toBe("something_new");
    expect(auditScopeText({ driver_id: "drv-001", device_id: null, action: "read_events" })).toBe("Tài xế drv-001");
    expect(auditScopeText({ driver_id: null, device_id: null, action: "read_stats" })).toBe("Cả đội xe");
    expect(auditScopeText({ driver_id: null, device_id: null, action: "update_thresholds" })).toBe("–");
    expect(auditScopeText({ driver_id: "drv-001", device_id: "cam-001", action: "read_trip_report" })).toBe(
      "Tài xế drv-001 (thiết bị cam-001)",
    );
  });

  it("tells every dashboard user that reads are logged", () => {
    const note = policyNote({ retention_events_days: 60, retention_summaries_days: 365, retention_access_log_days: 365 });
    expect(note).toContain("nhật ký truy cập");
    expect(policyNote({ retention_events_days: 60, retention_summaries_days: 365 })).not.toContain("nhật ký truy cập");
  });
});
