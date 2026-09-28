import { useCallback, useEffect, useRef, useState } from "react";
import type { HudAlert, HudSnapshot } from "../lib/types";
import { ALARM_REPEAT_S, play, playAlert, systemSound, unlock } from "./chime";
import { demoSnapshot } from "./demo";
import { edgeSource, type HudSource } from "./edge";
import HudView from "./HudView";
import type { HudLink } from "./hudModel";

const POLL_MS = 300;
const STALE_S = 3; // no update from the camera loop for this long = frozen

type Mode = "live" | "demo";

// windowS comes from the device (thresholds.yaml hud.feedback_window_s); without it the device decides.
function feedbackTarget(alerts: HudAlert[], now: number, windowS: number | undefined): HudAlert | null {
  const newest = alerts[0];
  if (!newest || newest.feedback || (windowS != null && now - newest.at > windowS)) return null;
  return newest;
}

export default function HudScreen({ source = edgeSource }: { source?: HudSource }) {
  const [mode, setMode] = useState<Mode>("live");
  const [link, setLink] = useState<HudLink>("connecting");
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
        const s = await source.state(ctrl.signal);
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
  }, [mode, source]);

  // Sound for alerts not heard yet: its own sound per kind of alert (chime.ts).
  useEffect(() => {
    const newest = snap?.alerts[0];
    if (!newest || seenAlerts.current.has(newest.event_id)) return;
    const firstLoad = seenAlerts.current.size === 0 && (snap?.alerts.length ?? 0) > 1;
    snap?.alerts.forEach((a) => seenAlerts.current.add(a.event_id));
    if (sound && !firstLoad) playAlert(newest.level, newest.reasons);
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
    const result = await source.falseAlarm(target.event_id);
    setToast(
      {
        recorded: "Đã ghi nhận cảnh báo sai. Cảm ơn bạn!",
        duplicate: "Cảnh báo này đã được báo sai trước đó",
        expired: "Đã quá thời gian để báo sai cảnh báo này",
        unknown: "Thiết bị không còn giữ cảnh báo này",
        offline: "Mất kết nối với thiết bị, thử lại sau",
      }[result],
    );
  }, [target, mode, source]);

  const stale = mode === "live" && snap?.updated_at != null && now - snap.updated_at > STALE_S;
  const level = snap?.connected ? snap.level : 0;
  const cameraLost = mode === "live" && link === "ok" && snap?.camera_lost === true;
  const showPanel = link === "ok" && snap?.connected && !stale && !cameraLost;

  // L3 is a strong alarm: one siren is easy to sleep through, so repeat it while the
  // eyes are still closed (closed_duration > 0), and stop as soon as they open.
  const alarmOn = sound && !!showPanel && level === 3 && (snap?.eyes_closed_s ?? 0) > 0;
  useEffect(() => {
    if (!alarmOn) return;
    const id = setInterval(() => playAlert(3, []), ALARM_REPEAT_S * 1000);
    return () => clearInterval(id);
  }, [alarmOn]);

  // Camera lost / back: its own sound, the driver is not monitored meanwhile.
  const wasCameraLost = useRef(false);
  useEffect(() => {
    if (cameraLost === wasCameraLost.current) return;
    wasCameraLost.current = cameraLost;
    if (sound) play(systemSound(cameraLost ? "camera_lost" : "camera_restored"));
  }, [cameraLost, sound]);

  return (
    <HudView
      snap={snap}
      link={link}
      stale={stale}
      cameraLost={cameraLost}
      demo={mode === "demo"}
      now={now}
      sound={sound}
      feedbackTarget={target}
      toast={toast}
      edgeUrl={source.address}
      onToggleSound={() => setSound((on) => (on ? false : unlock()))}
      onToggleDemo={() => setMode((m) => (m === "live" ? "demo" : "live"))}
      onFalseAlarm={onFalseAlarm}
    />
  );
}
