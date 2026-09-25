import { useCallback, useEffect, useRef, useState } from "react";
import { ago, clockText, formatNumber } from "../lib/format";
import { LEVELS, reasonText } from "../lib/labels";
import type { HudAlert, HudSnapshot } from "../lib/types";
import { playAlert, unlock } from "./chime";
import { demoSnapshot } from "./demo";
import { EDGE_URL, fetchState, sendFalseAlarm } from "./edge";

const POLL_MS = 300;
const STALE_S = 3; // no update from the camera loop for this long = frozen

type Mode = "live" | "demo";
type Link = "connecting" | "ok" | "down";

// windowS comes from the device (thresholds.yaml hud.feedback_window_s); without it the device decides.
function feedbackTarget(alerts: HudAlert[], now: number, windowS: number | undefined): HudAlert | null {
  const newest = alerts[0];
  if (!newest || newest.feedback || (windowS != null && now - newest.at > windowS)) return null;
  return newest;
}

export default function HudScreen() {
  const [mode, setMode] = useState<Mode>("live");
  const [link, setLink] = useState<Link>("connecting");
  const [snap, setSnap] = useState<HudSnapshot | null>(null);
  const [sound, setSound] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [now, setNow] = useState(Date.now() / 1000);
  const failures = useRef(0);
  const seenAlerts = useRef<Set<string>>(new Set());
  const demoStart = useRef(Date.now());
  const demoFlags = useRef<Set<string>>(new Set());

  // Live: poll the edge agent. Demo: scripted states.
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      setNow(Date.now() / 1000);
      if (mode === "demo") {
        setSnap(demoSnapshot((Date.now() - demoStart.current) / 1000, demoFlags.current));
        setLink("ok");
        return;
      }
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 1000);
      try {
        const s = await fetchState(ctrl.signal);
        if (cancelled) return;
        failures.current = 0;
        setSnap(s);
        setLink("ok");
      } catch {
        if (cancelled) return;
        failures.current += 1;
        if (failures.current >= 3) setLink("down");
      } finally {
        clearTimeout(timer);
      }
    };
    void tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [mode]);

  // Sound for alerts not heard yet.
  useEffect(() => {
    const newest = snap?.alerts[0];
    if (!newest || seenAlerts.current.has(newest.event_id)) return;
    const firstLoad = seenAlerts.current.size === 0 && (snap?.alerts.length ?? 0) > 1;
    snap?.alerts.forEach((a) => seenAlerts.current.add(a.event_id));
    if (sound && !firstLoad) playAlert(newest.level);
  }, [snap, sound]);

  useEffect(() => {
    if (!toast) return;
    const id = setTimeout(() => setToast(null), 3500);
    return () => clearTimeout(id);
  }, [toast]);

  const target = snap ? feedbackTarget(snap.alerts, now, snap.feedback_window_s) : null;

  const onFalseAlarm = useCallback(async () => {
    if (!target) return;
    if (mode === "demo") {
      demoFlags.current.add(target.event_id);
      setToast("Đã ghi nhận cảnh báo sai (mô phỏng)");
      return;
    }
    const result = await sendFalseAlarm(target.event_id);
    setToast(
      {
        recorded: "Đã ghi nhận cảnh báo sai. Cảm ơn bạn!",
        duplicate: "Cảnh báo này đã được báo sai trước đó",
        expired: "Đã quá thời gian để báo sai cảnh báo này",
        unknown: "Thiết bị không còn giữ cảnh báo này",
        offline: "Mất kết nối với thiết bị, thử lại sau",
      }[result],
    );
  }, [target, mode]);

  const stale = mode === "live" && snap?.updated_at != null && now - snap.updated_at > STALE_S;
  const level = snap?.connected ? snap.level : 0;
  const info = LEVELS[level];
  const cameraLost = mode === "live" && link === "ok" && snap?.camera_lost === true;
  const showPanel = link === "ok" && snap?.connected && !stale && !cameraLost;

  return (
    <div className="hud" data-level={showPanel ? level : "off"}>
      <header className="hud-bar">
        <span className="hud-brand">DriverGuard</span>
        <span className={`hud-link hud-link-${link}`} role="status">
          <span className="dot" aria-hidden />
          {mode === "demo" ? "Mô phỏng" : link === "ok" ? "Đã kết nối thiết bị" : link === "down" ? "Mất kết nối" : "Đang kết nối…"}
        </span>
        <span className="hud-clock">{clockText(snap?.clock_hour)}</span>
        <button
          type="button"
          className="hud-chip"
          aria-pressed={sound}
          onClick={() => setSound((on) => (on ? false : unlock()))}
        >
          {sound ? "Âm thanh: bật" : "Bật âm thanh"}
        </button>
        <button type="button" className="hud-chip" onClick={() => setMode((m) => (m === "live" ? "demo" : "live"))}>
          {mode === "live" ? "Chạy mô phỏng" : "Về thiết bị thật"}
        </button>
        <a className="hud-chip" href="#/dashboard">
          Dashboard
        </a>
      </header>

      {showPanel ? (
        <main className="hud-main">
          <section className={`hud-level level-${level}`} aria-live="assertive">
            <div className="hud-level-icon" aria-hidden>
              {info.icon}
            </div>
            <div>
              <div className="hud-level-code">{info.short}</div>
              <div className="hud-level-title">{info.title}</div>
              <div className="hud-level-action">{info.action}</div>
              {snap.reasons.length > 0 && (
                <ul className="hud-reasons">
                  {snap.reasons.map((r) => (
                    <li key={r}>{reasonText(r)}</li>
                  ))}
                </ul>
              )}
            </div>
          </section>

          <section className="hud-gauges" aria-label="Thông số">
            <Gauge label="Tốc độ" value={formatNumber(snap.speed_kmh ?? null)} unit="km/h" />
            <Gauge label="Buồn ngủ" value={formatNumber(snap.drowsy_score)} unit="/100" />
            <Gauge label="Mất tập trung" value={formatNumber(snap.distraction_score)} unit="/100" />
            <Gauge label="Mắt nhắm" value={formatNumber(snap.eyes_closed_s, 1)} unit="giây" />
          </section>

          <section className="hud-feedback">
            <button type="button" className="hud-false-alarm" disabled={!target} onClick={onFalseAlarm}>
              Cảnh báo sai
            </button>
            <p className="hud-feedback-note">
              {target
                ? `Cho cảnh báo ${LEVELS[target.level].short} · ${target.reasons.map(reasonText).join(", ")} · ${ago(now - target.at)}`
                : snap.alerts[0]?.feedback
                  ? "Đã ghi nhận: cảnh báo gần nhất là cảnh báo sai"
                  : "Chưa có cảnh báo nào để báo sai"}
            </p>
            {snap.alerts.length > 0 && (
              <ol className="hud-recent" aria-label="Cảnh báo gần đây">
                {snap.alerts.slice(0, 4).map((a) => (
                  <li key={a.event_id}>
                    <span className={`badge level-${a.level}`}>
                      <span aria-hidden>{LEVELS[a.level].icon}</span> {LEVELS[a.level].short}
                    </span>
                    <span>{a.reasons.map(reasonText).join(", ")}</span>
                    <span className="muted">{ago(now - a.at)}</span>
                    {a.feedback && <span className="tag">Đã báo sai</span>}
                  </li>
                ))}
              </ol>
            )}
          </section>
        </main>
      ) : (
        <main className="hud-offline">
          <p className="hud-offline-title">
            {cameraLost
              ? "Mất camera: hệ thống đang không giám sát, đang kết nối lại…"
              : stale
                ? "Không nhận dữ liệu từ camera"
                : link === "down" ? "Không kết nối được thiết bị" : "Đang kết nối thiết bị…"}
          </p>
          <p className="muted">
            HUD đọc trạng thái từ edge agent tại <code>{EDGE_URL}</code>. Chạy{" "}
            <code>python -m edge_agent.main --source 0</code> hoặc bấm “Chạy mô phỏng”.
          </p>
        </main>
      )}

      {toast && (
        <div className="hud-toast" role="status">
          {toast}
        </div>
      )}
    </div>
  );
}

function Gauge({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="gauge">
      <div className="gauge-label">{label}</div>
      <div className="gauge-value">
        {value} <span className="gauge-unit">{unit}</span>
      </div>
    </div>
  );
}
