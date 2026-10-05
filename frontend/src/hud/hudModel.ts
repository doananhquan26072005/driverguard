// Pure view-model helpers for the HUD (unit-tested in hudModel.test.ts). No thresholds here:
// the level and the reasons come from the edge agent, the HUD only decides what to show first.
import { ENROLL_HINTS, ENROLL_STEPS, ENROLL_TEXT } from "../lib/labels";
import type { EnrollStep, HudEnrollment, HudSnapshot, Level, Reason } from "../lib/types";

export type HudLink = "connecting" | "ok" | "down";
export type SystemState = "down" | "camera_lost" | "error" | "unavailable" | "stale" | "connecting";

/** Most urgent first: the headline shows one reason, the others go in the detail line. */
export const REASON_PRIORITY: readonly Reason[] = [
  "microsleep",
  "no_face",
  "phone",
  "off_road",
  "repeated_l1", // before the cause it repeats: the headline says the driver was told several times
  "drowsy_score",
  "trend",
  "blink_rate",
];

const DROWSY_REASONS: ReadonlySet<Reason> = new Set(["microsleep", "drowsy_score", "trend", "blink_rate", "repeated_l1"]);
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

/** Why the driver panel cannot be shown, or null when it can. Link down wins over a stale snapshot.
 *  "unavailable": the face is lost while moving (PRD FR-6), the driver is not monitored. */
export function systemState(
  link: HudLink,
  snap: HudSnapshot | null,
  stale: boolean,
  cameraLost: boolean,
): SystemState | null {
  if (link === "down") return "down";
  if (cameraLost) return "camera_lost";
  if (link === "ok" && snap?.connected && !stale && snap.processing_error) return "error"; // M28
  if (link === "ok" && snap?.connected && !stale && snap.unavailable) return "unavailable";
  if (stale) return "stale";
  if (link !== "ok" || !snap?.connected) return "connecting";
  return null;
}

export const ENROLL_STEP_ORDER: readonly EnrollStep[] = ["look_camera", "look_road", "close_eyes"];

export function enrollStep(e: HudEnrollment | undefined): EnrollStep | null {
  return e && (ENROLL_STEP_ORDER as readonly string[]).includes(e.status) ? (e.status as EnrollStep) : null;
}

/** The driver is no longer watched because the HUD lost the loop (M28): no data, no link, or frames
 *  failing. Each start of it is announced with a loud sound. */
export function monitoringStopped(state: SystemState | null): boolean {
  return state === "down" || state === "stale" || state === "error";
}

/** The vehicle link went quiet, driving or parked (M26): the HUD says so and plays a sound. */
export function vehicleSignalLost(snap: HudSnapshot | null): boolean {
  return snap?.vehicle?.signal_lost === true;
}

/** The consent screen (before the steps) replaces the status stage while no alert is up. */
export function showConsentPanel(e: HudEnrollment | undefined, level: Level): boolean {
  return level === 0 && e?.status === "consent";
}

/** The guided enrollment screen replaces the status stage, but never hides an alert. */
export function showEnrollPanel(e: HudEnrollment | undefined, level: Level): boolean {
  return level === 0 && enrollStep(e) !== null;
}

/** Small reminder while not enrolled (driving, or failed until the next stop), else null. */
export function enrollReminder(e: HudEnrollment | undefined): string | null {
  if (e?.status === "waiting") return ENROLL_TEXT.waiting;
  if (e?.status === "failed") return ENROLL_TEXT.failed;
  if (e?.status === "later") return ENROLL_TEXT.later;
  return null;
}

export interface EnrollCue {
  beep: boolean; // a step just ended (the driver may not be looking: step 3 has the eyes shut)
  say: string | null; // spoken prompt
}

/** What to play when the enrollment state changes from `prev` to `next`. */
export function enrollCue(prev: HudEnrollment | undefined, next: HudEnrollment | undefined): EnrollCue {
  const none: EnrollCue = { beep: false, say: null };
  if (!next) return none;
  const before = enrollStep(prev);
  const step = enrollStep(next);
  if (next.status === "done" && prev?.status !== "done" && prev) return { beep: true, say: ENROLL_TEXT.done };
  if (step && step !== before) return { beep: before !== null, say: ENROLL_STEPS[step].title };
  if (step && prev && next.attempts > prev.attempts && next.hint)
    return { beep: false, say: `${ENROLL_HINTS[next.hint]}. ${ENROLL_STEPS[step].title}` };
  if (next.status === "failed" && prev?.status !== "failed") return { beep: false, say: ENROLL_TEXT.failed };
  return none;
}
