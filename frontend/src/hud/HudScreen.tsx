import { useCallback, useEffect, useRef, useState } from "react";
import type { HudAlert, HudSnapshot, VehicleAction } from "../lib/types";
import { HUD_DEFAULTS } from "../lib/defaults";
import { armAudio, play, playAlert, setGain, speak, systemSound, unlock, type VoiceKey } from "./chime";
import { demoSnapshot } from "./demo";
import { edgeSource, type HudSource, type TripEnd } from "./edge";
import HudView from "./HudView";
import TripSummaryView from "./TripSummaryView";
import { alertVoiceKey, enrollCue, enrollVoiceKeys, type HudLink, hudCanLeave, monitoringStopped, presenceUp, systemState, vehicleSignalLost } from "./hudModel";

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
  askEnd?: number; // a new number asks "Kết thúc chuyến?" (#/live's "Dừng camera", M72)
}

export default function HudScreen({ source = edgeSource, onTripEnded, onDone, askEnd }: Props) {
  const [mode, setMode] = useState<Mode>("live");
  const [link, setLink] = useState<HudLink>("connecting");
  const [snap, setSnap] = useState<HudSnapshot | null>(null);
  const [sound, setSound] = useState(false); // sound is always on; false only while the browser blocks it
  const [toast, setToast] = useState<string | null>(null);
  const [tripEnd, setTripEnd] = useState<TripEnd | null>(null);
  const [ending, setEnding] = useState(false);
  const [now, setNow] = useState(Date.now() / 1000);
  const failures = useRef(0);
  const seenAlerts = useRef<Set<string>>(new Set());
  const firstState = useRef(true); // no state seen yet: what the first one lists was sounded before this HUD opened
  const unheard = useRef<{ alert: HudAlert; late: boolean } | null>(null); // an alert not sounded yet (sound blocked)
  const reasonsRef = useRef<HudSnapshot["reasons"]>([]); // the alert being repeated with the L3 siren
  const demoStart = useRef(Date.now());
  const demoFlags = useRef<Set<string>>(new Set());
  // The screen's own numbers (thresholds.yaml hud.*, M85): the agent's with every state, the build's
  // (lib/defaults) until the first one arrives. No number is kept here.
  const display = mode === "live" ? (snap?.display ?? HUD_DEFAULTS) : HUD_DEFAULTS;
  const displayRef = useRef(display);
  displayRef.current = display;
  // The spoken line follows the chime, not over it.
  const afterChime = useRef((f: () => void) => void setTimeout(f, displayRef.current.chime_to_voice_s * 1000)).current;
  const [g0, g1, g2, g3] = display.gain;
  useEffect(() => setGain([g0, g1, g2, g3]), [g0, g1, g2, g3]);

  // Sound on from the start; the first touch anywhere lifts the browser's block (chime.ts).
  useEffect(() => armAudio(setSound), []);

  // Live: poll the edge agent. Demo: scripted states.
  useEffect(() => {
    let cancelled = false;
    const tick = async () => {
      setNow(Date.now() / 1000);
      if (mode === "demo") {
        setSnap(demoSnapshot((Date.now() - demoStart.current) / 1000, demoFlags.current));
        setLink("ok");
      }
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), displayRef.current.state_timeout_s * 1000);
      try {
        const s = await source.state(ctrl.signal);
        if (cancelled) return;
        if (mode === "demo") {
          // M72: the demo was started with no device behind the screen. One that now watches a driver
          // takes the screen back: its alerts must not stay hidden behind scripted ones.
          if (s.connected) setMode("live");
          return;
        }
        failures.current = 0;
        setSnap(s);
        setLink("ok");
      } catch {
        if (cancelled || mode === "demo") return;
        failures.current += 1;
        if (failures.current >= displayRef.current.link_down_failures) setLink("down");
      } finally {
        clearTimeout(timer);
      }
    };
    void tick();
    const id = setInterval(tick, display.poll_s * 1000);
    // M50: a source that can push (#/live) hands over a new alert in the frame it is raised; the poll
    // goes on for the display and for noticing a loop that stopped.
    const unsubscribe =
      mode === "live"
        ? source.subscribe?.((s) => {
            if (cancelled) return;
            failures.current = 0;
            setNow(Date.now() / 1000);
            setSnap(s);
            setLink("ok");
          })
        : undefined;
    return () => {
      cancelled = true;
      clearInterval(id);
      unsubscribe?.();
    };
  }, [mode, source, display.poll_s]);

  // Sound for alerts not heard yet: its own sound per kind of alert (chime.ts).
  // - The alerts of the first state this HUD sees are history, however many (M100): a HUD opened in the
  //   middle of a trip does not sound an old alert again. Before, a list of exactly one did.
  // - An alert that comes while the browser still blocks sound waits for the first touch, and is then
  //   sounded if it is still the newest and a level is still up (M100). Before, it was never heard.
  useEffect(() => {
    if (!snap) return;
    const newest = snap.alerts[0];
    const history = firstState.current;
    firstState.current = false;
    if (newest && !seenAlerts.current.has(newest.event_id)) {
      snap.alerts.forEach((a) => seenAlerts.current.add(a.event_id));
      unheard.current = history ? null : { alert: newest, late: false };
    }
    const due = unheard.current;
    if (!due) return;
    if (!sound) {
      due.late = true;
      return;
    }
    unheard.current = null;
    if (due.late && (newest?.event_id !== due.alert.event_id || !(snap.connected && snap.level > 0))) return; // over meanwhile
    playAlert(due.alert.level, due.alert.reasons);
    afterChime(() => speak(alertVoiceKey(due.alert.reasons) as VoiceKey)); // what to do, in Vietnamese
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

  const stale = mode === "live" && snap?.updated_at != null && now - snap.updated_at > display.stale_s;
  const level = snap?.connected ? snap.level : 0;
  reasonsRef.current = snap?.reasons ?? [];
  const cameraLost = mode === "live" && link === "ok" && snap?.camera_lost === true;
  const showPanel = link === "ok" && snap?.connected && !stale && !cameraLost;

  // L3 is a strong alarm: one siren is easy to sleep through, so repeat it while the
  // eyes are still closed (closed_duration > 0), and stop as soon as they open.
  const alarmOn = sound && !!showPanel && level === 3 && (snap?.eyes_closed_s ?? 0) > 0;
  useEffect(() => {
    if (!alarmOn) return;
    const id = setInterval(() => {
      playAlert(3, []);
      afterChime(() => speak(alertVoiceKey(reasonsRef.current) as VoiceKey)); // the order again with the siren
    }, display.alarm_repeat_s * 1000);
    return () => clearInterval(id);
  }, [alarmOn, display.alarm_repeat_s]);

  // Camera lost / back: its own sound, the driver is not monitored meanwhile.
  const wasCameraLost = useRef(false);
  useEffect(() => {
    if (cameraLost === wasCameraLost.current) return;
    if (!sound && cameraLost) return; // blocked: kept as "not told yet", sounded with the first touch if it still holds (M100)
    wasCameraLost.current = cameraLost;
    if (sound) {
      play(systemSound(cameraLost ? "camera_lost" : "camera_restored"));
      afterChime(() => speak(cameraLost ? "sys.camera_lost" : "sys.camera_restored"));
    }
  }, [cameraLost, sound]);

  // Face lost while moving (FR-6): not an alert, but the driver must know monitoring stopped.
  const unavailable = !!showPanel && snap?.unavailable === true;
  const wasUnavailable = useRef(false);
  useEffect(() => {
    if (unavailable === wasUnavailable.current) return;
    if (!sound && unavailable) return; // blocked: kept as "not told yet", sounded with the first touch if it still holds (M100)
    wasUnavailable.current = unavailable;
    if (sound) {
      play(systemSound(unavailable ? "monitoring_unavailable" : "monitoring_restored"));
      afterChime(() => speak(unavailable ? "sys.unavailable" : "sys.restored"));
    }
  }, [unavailable, sound]);

  // "Bạn còn ở đó không?" (M44): the question is repeated until the driver taps or is seen again;
  // unanswered, the L3 siren takes over (a passenger may hear it).
  const presence = mode === "live" ? presenceUp(systemState(link, snap, stale, cameraLost), snap) : null;
  useEffect(() => {
    if (!presence || !sound) return;
    const ring = () => {
      if (presence === "asking") {
        play(systemSound("presence"));
        afterChime(() => speak("sys.presence"));
      } else playAlert(3, []);
    };
    ring();
    const id = setInterval(ring, display.presence_repeat_s * 1000);
    return () => clearInterval(id);
  }, [presence, sound, display.presence_repeat_s]);

  // The HUD lost the loop (M28): no data for hud.stale_s, no link to the device, or frames failing. Each
  // start is loud (the driver is not watched), its end the usual "restored" tone. Not after the trip ended.
  const stopped = mode === "live" && !tripEnd && !snap?.trip_ended && monitoringStopped(systemState(link, snap, stale, cameraLost));
  const wasStopped = useRef(false);
  useEffect(() => {
    if (stopped === wasStopped.current) return;
    if (!sound && stopped) return; // blocked: kept as "not told yet", sounded with the first touch if it still holds (M100)
    wasStopped.current = stopped;
    if (sound) {
      play(systemSound(stopped ? "monitoring_stopped" : "monitoring_restored"));
      afterChime(() => speak(stopped ? "sys.stopped" : "sys.restored"));
    }
  }, [stopped, sound]);

  // Vehicle link lost / back (M26), driving or parked: the driver is told (while driving it is still
  // monitored as moving).
  const signalLost = mode === "live" && link === "ok" && vehicleSignalLost(snap);
  const wasSignalLost = useRef(false);
  useEffect(() => {
    if (signalLost === wasSignalLost.current) return;
    if (!sound && signalLost) return; // blocked: kept as "not told yet", sounded with the first touch if it still holds (M100)
    wasSignalLost.current = signalLost;
    if (sound) {
      play(systemSound(signalLost ? "vehicle_signal_lost" : "vehicle_signal_restored"));
      afterChime(() => speak(signalLost ? "sys.vehicle_lost" : "sys.vehicle_restored"));
    }
  }, [signalLost, sound]);

  // Driver enrollment: steps 2 and 3 are done without looking at the screen, so each prompt
  // is spoken and the end of a step beeps (step 3: "open your eyes").
  const lastEnroll = useRef(snap?.enrollment);
  useEffect(() => {
    if (mode !== "live") return;
    const cue = enrollCue(lastEnroll.current, snap?.enrollment);
    const lines = enrollVoiceKeys(lastEnroll.current, snap?.enrollment) as VoiceKey[];
    lastEnroll.current = snap?.enrollment;
    if (!sound) return;
    if (cue.beep) play(systemSound("enroll_beep"));
    if (lines.length) (cue.beep ? afterChime : (f: () => void) => f())(() => speak(...lines));
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

  // "Đổi tài xế" and the enrollment consent answer: the agent applies them, the next snapshot shows it.
  const onVehicle = useCallback(
    async (action: VehicleAction) => {
      if (!source.vehicle) return;
      const ok = await source.vehicle(action);
      // A second tap on the consent screen finds nothing to answer: not worth a toast.
      if (!ok && action === "change_driver") setToast("Thiết bị không nhận lệnh, thử lại");
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
      camera={mode === "live" ? (source.cameraStream?.() ?? null) : null}
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
      onEnableSound={() => unlock()}
      onToggleDemo={
        hudCanLeave(link, snap, mode === "demo", !!source.cameraStream) ? () => setMode((m) => (m === "live" ? "demo" : "live")) : undefined
      }
      askEnd={mode === "live" && source.endTrip ? askEnd : undefined}
      onFalseAlarm={onFalseAlarm}
      onEndTrip={mode === "live" && source.endTrip ? onEndTrip : undefined}
      onVehicle={mode === "live" && source.vehicle ? onVehicle : undefined}
      ending={ending}
    />
  );
}
