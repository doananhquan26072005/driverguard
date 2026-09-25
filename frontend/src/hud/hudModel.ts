// Pure view-model helpers for the HUD (unit-tested in hudModel.test.ts). No thresholds here:
// the level and the reasons come from the edge agent, the HUD only decides what to show first.
import type { HudSnapshot, Reason } from "../lib/types";

export type HudLink = "connecting" | "ok" | "down";
export type SystemState = "down" | "camera_lost" | "stale" | "connecting";

/** Most urgent first: the headline shows one reason, the others go in the detail line. */
export const REASON_PRIORITY: readonly Reason[] = [
  "microsleep",
  "no_face",
  "phone",
  "off_road",
  "drowsy_score",
  "trend",
  "blink_rate",
];

const DROWSY_REASONS: ReadonlySet<Reason> = new Set(["microsleep", "drowsy_score", "trend", "blink_rate"]);
const DISTRACTION_REASONS: ReadonlySet<Reason> = new Set(["off_road", "phone", "no_face"]);

export function primaryReason(reasons: readonly Reason[]): Reason | null {
  for (const r of REASON_PRIORITY) if (reasons.includes(r)) return r;
  return reasons[0] ?? null;
}

/** Reasons in display order (primary first). */
export function orderedReasons(reasons: readonly Reason[]): Reason[] {
  const rank = (r: Reason) => {
    const i = REASON_PRIORITY.indexOf(r);
    return i === -1 ? REASON_PRIORITY.length : i;
  };
  return [...reasons].sort((a, b) => rank(a) - rank(b));
}

export const isDrowsyReason = (r: Reason) => DROWSY_REASONS.has(r);
export const isDistractionReason = (r: Reason) => DISTRACTION_REASONS.has(r);

/** Why the driver panel cannot be shown, or null when it can. Link down wins over a stale snapshot. */
export function systemState(
  link: HudLink,
  snap: HudSnapshot | null,
  stale: boolean,
  cameraLost: boolean,
): SystemState | null {
  if (link === "down") return "down";
  if (cameraLost) return "camera_lost";
  if (stale) return "stale";
  if (link !== "ok" || !snap?.connected) return "connecting";
  return null;
}
