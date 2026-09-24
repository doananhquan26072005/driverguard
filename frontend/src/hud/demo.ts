// Scripted HUD states for demos without a running edge agent (a 60 s loop).
import type { HudAlert, HudSnapshot, Level, Reason } from "../lib/types";

export const DEMO_CYCLE_S = 60;

interface Episode {
  start: number;
  end: number;
  level: Level;
  reasons: Reason[];
}

export const DEMO_SCRIPT: Episode[] = [
  { start: 10, end: 20, level: 1, reasons: ["drowsy_score"] },
  { start: 26, end: 34, level: 2, reasons: ["phone"] },
  { start: 40, end: 46, level: 3, reasons: ["microsleep"] },
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
      };
    })
    .reverse(); // newest first, like the edge server
  const drowsy = active?.reasons.includes("drowsy_score") ? 48 : active?.level === 3 ? 62 : 12;
  return {
    connected: true,
    updated_at: nowEpoch,
    level: active?.level ?? 0,
    reasons: active?.reasons ?? [],
    drowsy_score: drowsy,
    distraction_score: active?.reasons.includes("phone") ? 100 : 0,
    speed_kmh: 68 + 6 * Math.sin(elapsed / 9),
    clock_hour: 2.5 + elapsed / 3600,
    night: true,
    eyes_closed_s: active?.level === 3 ? Math.min(t - active.start + 1.5, 4) : 0,
    perclos_60s: 0.08,
    fps: 30,
    alerts,
  };
}
