import { useCallback, useEffect, useRef, useState } from "react";
import type { HudAlert, HudSnapshot, VehicleAction } from "../lib/types";
import { ALARM_REPEAT_S, play, playAlert, say, systemSound, unlock } from "./chime";
import { demoSnapshot } from "./demo";
import { edgeSource, type HudSource, type TripEnd } from "./edge";
import HudView from "./HudView";
import TripSummaryView from "./TripSummaryView";
import { enrollCue, type HudLink } from "./hudModel";

const POLL_MS = 300;
const STALE_S = 3; // no update from the camera loop for this long = frozen

type Mode = "live" | "demo";

// windowS comes from the device (thresholds.yaml hud.feedback_window_s); without it the device decides.
function feedbackTarget(alerts: HudAlert[], now: number, windowS: number | undefined): HudAlert | null {
  const newest = alerts[0];
  if (!newest || newest.feedback || (windowS != null && now - newest.at > windowS)) return null;
  return newest;
}

interface Props {
  source?: HudSource;
  onTripEnded?: () => void; // the camera stopped: e.g. #/live hides its self-view
  onDone?: () => void; // "Xong" on the trip summary
}

export default function HudScreen({ source = edgeSource, onTripEnded, onDone }: Props) {
  const [mode, setMode] = useState<Mode>("live");
  const [link, setLink] = useState<HudLink>("connecting");
  const [snap, setSnap] = useState<HudSnapshot | null>(null);
  const [sound, setSound] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [tripEnd, setTripEnd] = useState<TripEnd | null>(null);
  const [ending, setEnding] = useState(false);
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

  // Face lost while moving (FR-6): not an alert, but the driver must know monitoring stopped.
  const unavailable = !!showPanel && snap?.unavailable === true;
  const wasUnavailable = useRef(false);
  useEffect(() => {
    if (unavailable === wasUnavailable.current) return;
    wasUnavailable.current = unavailable;
    if (sound) play(systemSound(unavailable ? "monitoring_unavailable" : "monitoring_restored"));
  }, [unavailable, sound]);

  // Driver enrollment: steps 2 and 3 are done without looking at the screen, so each prompt
  // is spoken and the end of a step beeps (step 3: "open your eyes").
  const lastEnroll = useRef(snap?.enrollment);
  useEffect(() => {
    if (mode !== "live") return;
    const cue = enrollCue(lastEnroll.current, snap?.enrollment);
    lastEnroll.current = snap?.enrollment;
    if (!sound) return;
    if (cue.beep) play(systemSound("enroll_beep"));
    if (cue.say) say(cue.say);
  }, [snap, sound, mode]);

  // "Kết thúc chuyến": the agent builds the trip summary, sends it to the higher roles, stops.
  const onEndTrip = useCallback(async () => {
    if (!source.endTrip || ending) return;
    setEnding(true);
    try {
      const result = await source.endTrip();
      setTripEnd(result);
      onTripEnded?.();
    } catch {
      setToast("Không kết thúc được chuyến: thiết bị không trả lời");
    } finally {
      setEnding(false);
    }
  }, [source, ending, onTripEnded]);

  // "Tạm dừng" / "Tiếp tục lái" / "Đổi tài xế": the agent applies it, the next snapshot shows it.
  const onVehicle = useCallback(
    async (action: VehicleAction) => {
      if (!source.vehicle) return;
      const ok = await source.vehicle(action);
      if (!ok) setToast("Thiết bị không nhận lệnh, thử lại");
      else if (action === "change_driver") setToast("Người lái mới: nhìn thẳng vào camera để đăng ký");
    },
    [source],
  );

  if (tripEnd) {
    return (
      <TripSummaryView
        summary={tripEnd.summary}
        delivery={tripEnd.delivery}
        onDone={() => (onDone ? onDone() : setTripEnd(null))}
      />
    );
  }

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
      onEndTrip={mode === "live" && source.endTrip ? onEndTrip : undefined}
      onVehicle={mode === "live" && source.vehicle ? onVehicle : undefined}
      ending={ending}
    />
  );
}
