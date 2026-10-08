// #/hud-preview: every HUD state on demand, for design review, screenshots and the comprehension
// session of PRD FR-17. Fixed snapshots only (no edge agent, no sound played); the live screen
// stays #/hud. Every state picked by hand is logged with the tags `simulated` + `forced`
// (forcedLog.ts); the log stays in this page and in the file the operator downloads.
import { useEffect, useState } from "react";
import type { HudAlert, HudSnapshot, Level, Reason } from "../lib/types";
import { demoAlertMetrics, demoTrip, demoTripSummary } from "./demo";
import { appendForced, forcedEntry, forcedLogFile, type ForcedEntry } from "./forcedLog";
import HudView from "./HudView";
import TripSummaryView from "./TripSummaryView";
import type { HudLink } from "./hudModel";
import { HUD_DEFAULTS } from "../lib/defaults";

interface Scenario {
  key: string;
  label: string;
  level?: Level;
  reasons?: Reason[];
  patch?: Partial<HudSnapshot>;
  link?: HudLink;
  cameraLost?: boolean;
  soundBlocked?: boolean; // the browser still blocks sound: the amber touch-to-enable strip
}

const SCENARIOS: Scenario[] = [
  { key: "l0", label: "L0" },
  { key: "l1", label: "L1 buồn ngủ", level: 1, reasons: ["drowsy_score"], patch: { drowsy_score: 52 } },
  { key: "l1t", label: "L1 xu hướng", level: 1, reasons: ["trend"], patch: { drowsy_score: 41 } },
  { key: "l2o", label: "L2 nhìn lệch", level: 2, reasons: ["off_road"], patch: { distraction_score: 100 } },
  { key: "l2p", label: "L2 điện thoại", level: 2, reasons: ["phone", "off_road"], patch: { distraction_score: 100 } },
  { key: "off", label: "Tạm ngưng (mất mặt)", patch: { unavailable: true, unavailable_reason: "no_face" } },
  { key: "offc", label: "Tạm ngưng (che camera)", patch: { unavailable: true, unavailable_reason: "camera_blocked" } },
  { key: "offd", label: "Tạm ngưng (mặt tối)", patch: { unavailable: true, unavailable_reason: "low_light" } },
  { key: "offg", label: "Tạm ngưng (chói)", patch: { unavailable: true, unavailable_reason: "glare" } },
  { key: "offb", label: "Tạm ngưng (ảnh mờ)", patch: { unavailable: true, unavailable_reason: "blur" } },
  {
    key: "ask",
    label: "Bạn còn ở đó không?",
    patch: { unavailable: true, unavailable_reason: "no_face", presence: { asking: true, remaining_s: 8, unanswered: false } },
  },
  {
    key: "ask2",
    label: "Không trả lời",
    patch: { unavailable: true, unavailable_reason: "no_face", presence: { asking: false, remaining_s: 0, unanswered: true } },
  },
  { key: "l3u", label: "L3 không phản ứng", level: 3, reasons: ["unresponsive", "microsleep"], patch: { drowsy_score: 71 } },
  { key: "mute", label: "Chưa có tiếng", soundBlocked: true },
  { key: "err", label: "Lỗi xử lý", patch: { processing_error: true } },
  { key: "slow", label: "Máy chậm", patch: { low_fps: true } },
  { key: "nophone", label: "Mất dò điện thoại", patch: { phone_unavailable: true } },
  { key: "l3", label: "L3 ngủ gật", level: 3, reasons: ["microsleep"], patch: { drowsy_score: 71 } },
  {
    key: "en0",
    label: "Đăng ký: xác nhận",
    patch: { speed_kmh: 0, enrollment: { status: "consent", progress: 0, hint: null, attempts: 0 } },
  },
  {
    key: "en1",
    label: "Đăng ký 1",
    patch: { speed_kmh: 0, enrollment: { status: "look_camera", progress: 0.4, hint: null, attempts: 0 } },
  },
  {
    key: "en2",
    label: "Đăng ký 2 (giữ yên)",
    patch: { speed_kmh: 0, enrollment: { status: "look_road", progress: 0.2, hint: "hold_still", attempts: 1 } },
  },
  {
    key: "en3",
    label: "Đăng ký 3",
    patch: { speed_kmh: 0, enrollment: { status: "close_eyes", progress: 0.7, hint: null, attempts: 0 } },
  },
  {
    key: "enw",
    label: "Chưa đăng ký",
    patch: { enrollment: { status: "waiting", progress: 0, hint: "stop_vehicle", attempts: 0 } },
  },
  {
    key: "turnl",
    label: "Xi nhan trái",
    patch: { speed_kmh: 32, vehicle: { source: "sim", connected: true, speed_kmh: 32, turn_signal: "left", driving: true } },
  },
  {
    key: "park",
    label: "Đỗ, chưa có tín hiệu xe",
    patch: { speed_kmh: 0, vehicle: { source: "sim", connected: false, speed_kmh: 0, turn_signal: null, driving: false } },
  },
  {
    key: "lost",
    label: "Mất tín hiệu xe",
    patch: {
      speed_kmh: null,
      vehicle: { source: "sim", connected: false, speed_kmh: null, turn_signal: null, driving: true, signal_lost: true },
    },
  },
  { key: "cam", label: "Mất camera", cameraLost: true },
  { key: "trip", label: "Tổng kết chuyến" },
  { key: "down", label: "Mất kết nối", link: "down" },
];

function snapshotFor(s: Scenario, night: boolean, now: number, since: number): HudSnapshot {
  const level = s.level ?? 0;
  const alerts: HudAlert[] = level
    ? [{ event_id: `preview-${s.key}`, level, reasons: s.reasons ?? [], at: since, feedback: null, metrics: demoAlertMetrics(s.reasons ?? []) }]
    : [];
  return {
    connected: true,
    updated_at: now,
    level,
    reasons: s.reasons ?? [],
    drowsy_score: 12,
    distraction_score: 3,
    speed_kmh: 68,
    clock_hour: night ? 2.5 : 14.25,
    night,
    dim: night,
    eyes_closed_s: level === 3 ? Math.min(1.5 + (now - since), 6) : 0,
    perclos_60s: 0.06,
    fps: 30,
    feedback_window_s: HUD_DEFAULTS.feedback_window_s,
    vehicle: {
      source: "sim",
      connected: true,
      speed_kmh: s.patch?.speed_kmh ?? 68,
      turn_signal: null,
      driving: !s.patch || s.patch.speed_kmh !== 0,
    },
    trip: demoTrip(level === 1 ? 7500 : 4320, level === 1 ? (s.patch?.drowsy_score ?? 52) : null),
    alerts,
    ...s.patch,
  };
}

// #/hud-preview?s=l3&night=0 opens a scenario directly (screenshots).
function hashParams(): URLSearchParams {
  return new URLSearchParams(window.location.hash.split("?")[1] ?? "");
}

export default function HudPreview() {
  const [key, setKey] = useState(() => hashParams().get("s") ?? "l0");
  const [night, setNight] = useState(() => hashParams().get("night") !== "0");
  const [since, setSince] = useState(() => Date.now() / 1000);
  const [now, setNow] = useState(() => Date.now() / 1000);
  const [toast, setToast] = useState<string | null>(null);
  const [forced, setForced] = useState<ForcedEntry[]>([]); // FR-17: states set by hand, never sent anywhere

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000), 250);
    return () => clearInterval(id);
  }, []);
  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 2500);
    return () => clearTimeout(id);
  }, [toast]);

  const scenario = SCENARIOS.find((s) => s.key === key) ?? SCENARIOS[0];
  const snap = snapshotFor(scenario, night, now, since);
  const pick = (k: string) => {
    const label = SCENARIOS.find((s) => s.key === k)?.label ?? k;
    setForced((log) => appendForced(log, forcedEntry(k, label, key, night)));
    setKey(k);
    setSince(Date.now() / 1000);
  };
  const downloadForced = () => {
    const url = URL.createObjectURL(new Blob([forcedLogFile(forced)], { type: "application/json" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `driverguard-forced-states-${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <>
      {key === "trip" ? (
        <TripSummaryView summary={demoTripSummary()} delivery="sent" onDone={() => pick("l0")} />
      ) : (
      <HudView
        snap={snap}
        link={scenario.link ?? "ok"}
        stale={false}
        cameraLost={scenario.cameraLost ?? false}
        demo={false}
        now={now}
        sound={!scenario.soundBlocked}
        feedbackTarget={snap.alerts[0] ?? null}
        toast={toast}
        edgeUrl="(xem trước)"
        onEnableSound={() => undefined}
        onToggleDemo={() => undefined}
        onFalseAlarm={() => setToast("Đã ghi nhận cảnh báo sai (xem trước)")}
        onEndTrip={() => pick("trip")}
        onVehicle={(action) =>
          action === "enroll_start"
            ? pick("en1")
            : setToast(action === "enroll_later" ? "Để sau (xem trước)" : "Đổi tài xế (xem trước)")
        }
      />
      )}
      <nav
        aria-label="Kịch bản xem trước"
        className="fixed inset-x-2 bottom-2 z-40 flex flex-wrap justify-center gap-1 rounded-hud-sm bg-black/70 p-1.5 font-hud text-[13px] text-white backdrop-blur"
      >
        {SCENARIOS.map((s) => (
          <button
            key={s.key}
            type="button"
            aria-pressed={s.key === key}
            onClick={() => pick(s.key)}
            className={`rounded-lg border-0 px-2.5 py-1.5 ${s.key === key ? "bg-white text-black" : "bg-transparent text-white hover:bg-white/15"}`}
          >
            {s.label}
          </button>
        ))}
        <button
          type="button"
          aria-pressed={night}
          onClick={() => setNight((n) => !n)}
          className="rounded-lg border-0 bg-transparent px-2.5 py-1.5 text-white ring-1 ring-white/30"
        >
          {night ? "Đêm" : "Ngày"}
        </button>
        <button
          type="button"
          onClick={downloadForced}
          disabled={forced.length === 0}
          title="Nhật ký các trạng thái đã ép tay (tag simulated + forced). Không gửi lên máy chủ, không tính vào số liệu."
          className="rounded-lg border-0 bg-transparent px-2.5 py-1.5 text-white ring-1 ring-white/30 disabled:opacity-40"
        >
          Tải nhật ký ép tay ({forced.length})
        </button>
      </nav>
    </>
  );
}
