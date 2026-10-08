// Scripted HUD states for demos without a running edge agent (a 90 s loop). Every kind of
// alert appears once, so each alert sound (chime.ts) can be heard (sound is always on); from
// UNAVAILABLE_FROM to UNAVAILABLE_TO the face is lost (monitoring unavailable, no alert).
import type { HudAlert, HudSnapshot, HudTrip, Level, Reason, TripSummary } from "../lib/types";
import { DEFAULTS, HUD_DEFAULTS } from "../lib/defaults";

export const DEMO_CYCLE_S = 90;
const [UNAVAILABLE_FROM, UNAVAILABLE_TO] = [46, 52];

interface Episode {
  start: number;
  end: number;
  level: Level;
  reasons: Reason[];
}

export const DEMO_SCRIPT: Episode[] = [
  { start: 8, end: 16, level: 1, reasons: ["drowsy_score"] },
  { start: 22, end: 28, level: 2, reasons: ["off_road"] },
  { start: 34, end: 40, level: 2, reasons: ["phone"] },
  { start: 58, end: 64, level: 3, reasons: ["microsleep"] },
  { start: 72, end: 78, level: 1, reasons: ["trend"] },
];

/** HUD snapshot `elapsed` seconds after the demo started. `flagged` = event ids marked false alarm. */
export function demoSnapshot(elapsed: number, flagged: ReadonlySet<string>, nowEpoch = Date.now() / 1000): HudSnapshot {
  const cycle = Math.floor(elapsed / DEMO_CYCLE_S);
  const t = elapsed - cycle * DEMO_CYCLE_S;
  const active = DEMO_SCRIPT.find((e) => t >= e.start && t < e.end);
  const alerts: HudAlert[] = DEMO_SCRIPT.map((e, i) => ({ e, i }))
    .filter(({ e }) => e.start <= t)
    .map(({ e, i }): HudAlert => {
      const id = `demo-${cycle}-${i}`;
      return {
        event_id: id,
        level: e.level,
        reasons: e.reasons,
        at: nowEpoch - (t - e.start),
        feedback: flagged.has(id) ? "false_alarm" : null,
        metrics: demoAlertMetrics(e.reasons),
      };
    })
    .reverse(); // newest first, like the edge server
  const drowsy = active?.level === 1 ? 48 : active?.level === 3 ? 62 : 12;
  return {
    connected: true,
    updated_at: nowEpoch,
    level: active?.level ?? 0,
    reasons: active?.reasons ?? [],
    drowsy_score: drowsy,
    distraction_score: active?.level === 2 ? 100 : 0,
    speed_kmh: 68 + 6 * Math.sin(elapsed / 9),
    clock_hour: 2.5 + elapsed / 3600,
    night: true,
    dim: true,
    eyes_closed_s: active?.level === 3 ? Math.min(t - active.start + 1.5, 4) : 0,
    perclos_60s: 0.08,
    fps: 30,
    unavailable: t >= UNAVAILABLE_FROM && t < UNAVAILABLE_TO,
    trip: demoTrip(4320 + elapsed, active?.level === 1 ? 48 : null),
    alerts,
  };
}

/** The numbers an agent attaches to an alert (M65), for the detail line. */
export function demoAlertMetrics(reasons: readonly Reason[]): NonNullable<HudAlert["metrics"]> {
  return {
    off_road_s: reasons.includes("off_road") ? 2.3 : reasons.includes("phone") ? 1.2 : 0,
    eyes_closed_s: reasons.includes("microsleep") ? 2.4 : 0,
    phone_ratio: reasons.includes("phone") ? 0.8 : 0,
    turn_signal: null,
  };
}

/** The agent's view of the running trip (M65): `driveS` of continuous driving, 15 minutes of fatigue
 *  rising gently; `lastScore` replaces the running minute (an alert in the demo). */
export function demoTrip(driveS: number, lastScore: number | null = null): HudTrip {
  const recent = Array.from({ length: DEFAULTS.hud.trend_minutes }, (_, i) => ({
    minute: 57 + i,
    drowsy_score: Math.round(11 + i * 1.6 + (i % 3) * 2),
    max_level: 0 as Level,
  }));
  const last = recent.length - 1;
  if (lastScore != null) recent[last] = { ...recent[last], drowsy_score: lastScore, max_level: 1 };
  const { score_l1, score_l2, trend_minutes } = DEFAULTS.hud;
  return { drive_run_s: driveS, driving_s: driveS, score_l1, score_l2, window_min: trend_minutes, recent_minutes: recent };
}

/** A 2 h 10 min trip for the summary screen preview (#/hud-preview?s=trip): tired from minute 95. */
export function demoTripSummary(): TripSummary {
  const minutes = Array.from({ length: 130 }, (_, m) => {
    const stopped = m >= 70 && m < 80;
    const score = stopped ? 5 : m < 60 ? 10 + m * 0.15 : m < 95 ? 18 + (m - 80) * 0.6 : 42 + (m - 95) * 0.5;
    return { minute: m, drowsy_score: Math.round(score), max_level: (score >= 40 ? 1 : 0) as Level, moving: !stopped };
  });
  return {
    trip_id: "trip-demo",
    started_at: "2026-10-01T08:00:00+07:00",
    ended_at: "2026-10-01T10:10:00+07:00",
    duration_s: 7800,
    driving_s: 7200,
    stopped_s: 600,
    rests: 1,
    longest_drive_s: 4200,
    avg_speed_kmh: 64,
    speed_source: "simulated",
    alerts_by_level: { "1": 2, "2": 1, "3": 0 },
    alerts_by_reason: { drowsy_score: 2, off_road: 1 },
    false_alarms: 0,
    microsleeps: 0,
    longest_closure_s: 0.5,
    yawns: 4,
    nods: 0,
    brow_raises: 2,
    off_road_s: 3,
    phone_s: 0,
    monitored_frac: 0.96,
    unavailable_s: 12,
    camera_lost_s: 0,
    enrolled: true,
    driver_changes: 0,
    drowsy_mean: 24,
    drowsy_p90: 49,
    drowsy_max: 59,
    first_tired_min: 95,
    score_l1: HUD_DEFAULTS.score_l1,
    score_l2: HUD_DEFAULTS.score_l2,
    rating: "attention",
    rating_reasons: ["tired_minutes"],
    suggestions: [{ code: "rest_after", minutes: 85 }, { code: "eyes_on_road" }],
    minutes,
  };
}
