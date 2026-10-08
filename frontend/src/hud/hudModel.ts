// Pure view-model helpers for the HUD (unit-tested in hudModel.test.ts). No thresholds here:
// the level and the reasons come from the edge agent, the HUD only decides what to show first.
import { ENROLL_HINTS, ENROLL_STEPS, ENROLL_TEXT } from "../lib/labels";
import type { EnrollStep, HudAlert, HudEnrollment, HudSnapshot, HudTrip, Level, Reason } from "../lib/types";

export type HudLink = "connecting" | "ok" | "down";
export type SystemState = "down" | "camera_lost" | "error" | "unavailable" | "stale" | "connecting";

/** Most urgent first: the headline shows one reason, the others go in the detail line. */
export const REASON_PRIORITY: readonly Reason[] = [
  "unresponsive", // the alarm did not wake the driver: the headline says stop now
  "repeated_l3",
  "microsleep",
  "no_face",
  "phone",
  "off_road",
  "repeated_l1", // before the cause it repeats: the headline says the driver was told several times
  "drowsy_score",
  "trend",
  "blink_rate",
];

const DROWSY_REASONS: ReadonlySet<Reason> = new Set([
  "microsleep",
  "unresponsive",
  "repeated_l3",
  "drowsy_score",
  "trend",
  "blink_rate",
  "repeated_l1",
]);
const DISTRACTION_REASONS: ReadonlySet<Reason> = new Set(["off_road", "phone", "no_face"]);

/** What the driver must hear or see without waiting for the next poll (M50): a new alert, another
 *  level, monitoring stopping or coming back, the presence question, an enrollment prompt. A source
 *  that can push (#/live) hands the snapshot over in the frame this key changes. */
export function urgentKey(snap: HudSnapshot): string {
  return [
    snap.level,
    snap.alerts[0]?.event_id ?? "",
    snap.unavailable ? (snap.unavailable_reason ?? "unavailable") : "",
    snap.camera_lost ? "camera_lost" : "",
    snap.processing_error ? "error" : "",
    snap.presence?.asking ? "asking" : snap.presence?.unanswered ? "unanswered" : "",
    snap.enrollment?.status ?? "",
    snap.enrollment?.hint ?? "",
  ].join("|");
}

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

/** May the HUD offer its two ways out, "Chạy mô phỏng" and the Dashboard link (M72)? Both take the
 *  screen, and with it every alert sound, away from the driver with one touch and no question. So only
 *  while nothing is watched from here: no device behind the screen yet (or the link is down), or the
 *  scripted demo itself (its button leads back). Never on #/live (`inPage`): leaving that page stops
 *  the camera. The demo and every state can always be seen on #/hud-preview. */
export function hudCanLeave(link: HudLink, snap: HudSnapshot | null, demo: boolean, inPage: boolean): boolean {
  if (inPage) return false;
  return demo || link !== "ok" || !snap?.connected;
}

/** "Bạn còn ở đó không?" is up (M44): asked, or asked and nobody answered. Only while the driver
 *  panel would show "unavailable" (not over a lost camera or a dead link). */
export function presenceUp(state: SystemState | null, snap: HudSnapshot | null): "asking" | "unanswered" | null {
  if (state !== "unavailable" || !snap?.presence) return null;
  if (snap.presence.asking) return "asking";
  return snap.presence.unanswered ? "unanswered" : null;
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

// ------------------------------------------------------------------ driving screens (M58)

/** Fatigue band of a drowsy_score against this trip's thresholds (risk.drowsy.l1 / l2 sent by the
 *  agent): 0 low, 1 tired (rest soon), 2 very tired. No threshold lives in the HUD. */
export type FatigueBand = 0 | 1 | 2;
export function fatigueBand(score: number, l1: number, l2: number): FatigueBand {
  return score >= l2 ? 2 : score >= l1 ? 1 : 0;
}

/** One bar of the fatigue chart: a judged minute, a minute with nothing judged (a rest, enrollment's
 *  eyes-closed step: a gap, not 0), or a slot before the trip started (nothing drawn). */
export type TrendSlot = { kind: "score"; score: number; band: FatigueBand; current: boolean } | { kind: "gap" } | { kind: "none" };

/** The chart's `window_min` slots, oldest first, the running minute last. */
export function trendSlots(trip: HudTrip | undefined): TrendSlot[] {
  if (!trip) return [];
  const recent = trip.recent_minutes;
  const width = Math.max(trip.window_min ?? recent.length, recent.length);
  const slots: TrendSlot[] = Array.from({ length: width - recent.length }, () => ({ kind: "none" }) as const);
  recent.forEach((m, i) =>
    slots.push(
      m == null
        ? { kind: "gap" }
        : {
            kind: "score",
            score: m.drowsy_score,
            band: fatigueBand(m.drowsy_score, trip.score_l1, trip.score_l2),
            current: i === recent.length - 1,
          },
    ),
  );
  return slots;
}

/** The chip of the fatigue card: what the recent minutes say, in a few words. */
export function fatigueSummary(trip: HudTrip | undefined, reasons: readonly Reason[], driving: boolean): { band: FatigueBand; text: string } {
  const last = trip?.recent_minutes.filter((m) => m != null).at(-1);
  const band = last && trip ? fatigueBand(last.drowsy_score, trip.score_l1, trip.score_l2) : 0;
  if (reasons.includes("trend")) return { band: Math.max(band, 1) as FatigueBand, text: "Mệt · đang tăng dần" };
  if (band === 2) return { band, text: "Rất mệt · dừng nghỉ ngay" };
  if (band === 1) return { band, text: "Mệt · nên nghỉ sớm" };
  return { band, text: driving ? "Thấp · chưa cần nghỉ" : "Thấp · xe đang đỗ" };
}

/** L3 action sentences are two lines: the order, then what to do ("Mở mắt!" / "Dừng xe nghỉ ngay"). */
export function splitAction(text: string): [string, string] {
  const bang = text.indexOf("! ");
  if (bang > 0) return [text.slice(0, bang + 1), text.slice(bang + 2)];
  const colon = text.indexOf(": ");
  if (colon > 0) return [text.slice(0, colon), text.slice(colon + 2).replace(/^./, (c) => c.toUpperCase())];
  return [text, ""];
}

/** The detail line under an L2 alert (M65 numbers): "Phát hiện lúc 15:40 · nhìn lệch 2,3 giây · không bật xi nhan". */
export function alertDetail(alert: HudAlert | undefined, timeOf: (epochS: number) => string, num: (v: number) => string): string | null {
  if (!alert) return null;
  const parts = [`Phát hiện lúc ${timeOf(alert.at)}`];
  const m = alert.metrics;
  if (m && m.off_road_s > 0) parts.push(`nhìn lệch ${num(m.off_road_s)} giây`);
  if (m && alert.reasons.includes("off_road"))
    parts.push(m.turn_signal ? `xi nhan ${m.turn_signal === "left" ? "trái" : "phải"}` : "không bật xi nhan");
  return parts.join(" · ");
}

/** What the left of the HUD's bottom bar says when no "false alarm" button is up, most useful first. */
export function footerNote(snap: HudSnapshot, labels: { signalLost: string | null; lowFps: string; phoneOff: string; enroll: string | null; lastAlert: string | null }): string {
  if (labels.signalLost) return labels.signalLost;
  if (snap.low_fps) return labels.lowFps;
  if (snap.phone_unavailable) return labels.phoneOff;
  if (labels.enroll) return labels.enroll;
  return labels.lastAlert ?? "Chưa có cảnh báo nào trong chuyến này";
}

// ------------------------------------------------------------------ plain words for the numbers (M58, review 07/10)
// Drivers do not read "52/100": each number is said in words, coloured by its band. The bands come
// from the agent (trip.score_l1 / l2) or from the alert itself; nothing here decides an alert.

export type Tone = "ok" | "caution" | "danger";

/** Drowsiness in words, banded by this trip's thresholds. */
export function drowsyWord(score: number | undefined, l1: number, l2: number): { word: string; tone: Tone } {
  const band = fatigueBand(score ?? 0, l1, l2);
  return band === 2 ? { word: "Rất mệt", tone: "danger" } : band === 1 ? { word: "Hơi mệt", tone: "caution" } : { word: "Tỉnh táo", tone: "ok" };
}

/** Attention in words: what the driver is doing now, from the active alert's reasons. */
export function attentionWord(reasons: readonly Reason[], level: Level): { word: string; tone: Tone } {
  const tone: Tone = level >= 2 ? "danger" : "caution";
  if (reasons.includes("phone")) return { word: "Cầm điện thoại", tone };
  if (reasons.includes("off_road")) return { word: "Nhìn lệch", tone };
  return { word: "Tập trung", tone: "ok" };
}

/** Eyes shut shorter than this are blinks: the tile keeps saying "Đang mở" (display only, no alert). */
export const EYES_SHOWN_CLOSED_S = 0.5;

/** The eyes in words: open, or shut for how long. */
export function eyesWord(closedS: number | undefined, num: (v: number) => string): { word: string; tone: Tone } {
  const s = closedS ?? 0;
  if (s < EYES_SHOWN_CLOSED_S) return { word: "Đang mở", tone: "ok" };
  return { word: `Nhắm ${num(s)} giây`, tone: s >= 1.5 ? "danger" : "caution" };
}

// ------------------------------------------------------------------ spoken lines (hud/voice-lines.json)

/** What an alert says aloud: its most urgent reason; null when there is no line for it. */
export function alertVoiceKey(reasons: readonly Reason[]): string | null {
  const primary = primaryReason(reasons);
  return primary ? `alert.${primary}` : null;
}

/** The lines of an enrollment cue: the hint first (what to fix), then the step. */
export function enrollVoiceKeys(prev: HudEnrollment | undefined, next: HudEnrollment | undefined): string[] {
  if (!next) return [];
  const step = enrollStep(next);
  const before = enrollStep(prev);
  if (next.status === "done" && prev?.status !== "done" && prev) return ["enroll.done"];
  if (step && step !== before) return [`enroll.${step}`];
  if (step && prev && next.attempts > prev.attempts && next.hint) return [`hint.${next.hint}`, `enroll.${step}`];
  if (next.status === "failed" && prev?.status !== "failed") return ["enroll.failed"];
  return [];
}
