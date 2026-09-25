// Scripted HUD states for demos without a running edge agent (a 90 s loop). Every kind of
// alert appears once, so each alert sound (chime.ts) can be heard with "Bật âm thanh".
import type { HudAlert, HudSnapshot, Level, Reason } from "../lib/types";

export const DEMO_CYCLE_S = 90;

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
  { start: 46, end: 52, level: 2, reasons: ["no_face"] },
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
    eyes_closed_s: active?.level === 3 ? Math.min(t - active.start + 1.5, 4) : 0,
    perclos_60s: 0.08,
    fps: 30,
    alerts,
  };
}
