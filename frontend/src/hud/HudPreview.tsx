// #/hud-preview: every HUD state on demand, for design review and screenshots. Fixed
// snapshots only (no edge agent, no sound); the live screen stays #/hud.
import { useEffect, useState } from "react";
import type { HudAlert, HudSnapshot, Level, Reason } from "../lib/types";
import { demoTripSummary } from "./demo";
import HudView from "./HudView";
import TripSummaryView from "./TripSummaryView";
import type { HudLink } from "./hudModel";

interface Scenario {
  key: string;
  label: string;
  level?: Level;
  reasons?: Reason[];
  patch?: Partial<HudSnapshot>;
  link?: HudLink;
  cameraLost?: boolean;
}

const SCENARIOS: Scenario[] = [
  { key: "l0", label: "L0" },
  { key: "l1", label: "L1 buồn ngủ", level: 1, reasons: ["drowsy_score"], patch: { drowsy_score: 52 } },
  { key: "l1t", label: "L1 xu hướng", level: 1, reasons: ["trend"], patch: { drowsy_score: 41 } },
  { key: "l2o", label: "L2 nhìn lệch", level: 2, reasons: ["off_road"], patch: { distraction_score: 100 } },
  { key: "l2p", label: "L2 điện thoại", level: 2, reasons: ["phone", "off_road"], patch: { distraction_score: 100 } },
  { key: "off", label: "Tạm ngưng (mất mặt)", patch: { unavailable: true } },
  { key: "l3", label: "L3 ngủ gật", level: 3, reasons: ["microsleep"], patch: { drowsy_score: 71 } },
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
  { key: "cam", label: "Mất camera", cameraLost: true },
  { key: "trip", label: "Tổng kết chuyến" },
  { key: "down", label: "Mất kết nối", link: "down" },
];

function snapshotFor(s: Scenario, night: boolean, now: number, since: number): HudSnapshot {
  const level = s.level ?? 0;
  const alerts: HudAlert[] = level
    ? [{ event_id: `preview-${s.key}`, level, reasons: s.reasons ?? [], at: since, feedback: null }]
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
    eyes_closed_s: level === 3 ? Math.min(1.5 + (now - since), 6) : 0,
    perclos_60s: 0.06,
    fps: 30,
    feedback_window_s: 120,
    vehicle: { manual: true, driving: !s.patch || s.patch.speed_kmh !== 0 },
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
    setKey(k);
    setSince(Date.now() / 1000);
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
        sound
        feedbackTarget={snap.alerts[0] ?? null}
        toast={toast}
        edgeUrl="(xem trước)"
        onToggleSound={() => undefined}
        onToggleDemo={() => undefined}
        onFalseAlarm={() => setToast("Đã ghi nhận cảnh báo sai (xem trước)")}
        onEndTrip={() => pick("trip")}
        onVehicle={(a) => setToast(a === "change_driver" ? "Đổi tài xế (xem trước)" : a === "park" ? "Tạm dừng (xem trước)" : "Tiếp tục lái (xem trước)")}
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
      </nav>
    </>
  );
}
