// Alert sounds with WebAudio (no audio files). Browsers only allow sound after a user
// gesture, so the HUD has a "Bật âm thanh" button that calls unlock().
//
// Each kind of alert has its own sound, so the driver knows what happened without looking:
// - drowsiness (drowsy_score, blink_rate): soft descending sine notes ("time to rest")
// - trend: one long soft note (fatigue rising slowly, suggest a break)
// - microsleep below L3 (red light: capped at L1): two low "wake up" pulses
// - off_road: rising two-note triangle, twice ("look ahead")
// - phone: fast high square beeps ("put the phone down")
// - no_face (v1 events only): low buzzing pulses (driver out of view)
// - L3 (microsleep): loud alternating siren, repeated while the eyes stay closed
// - camera lost / back: descending buzz / rising two notes (system, not the driver)
// - monitoring unavailable (face lost while moving) / back: low buzzing pulses / rising two notes
// - driver enrollment: one short clear beep when a step ends ("open your eyes" after step 3)
// The level sets the volume. alertSound() is pure (tested); play() does the WebAudio part.
import type { Level, Reason } from "../lib/types";

export type SoundKind =
  | "drowsy"
  | "trend"
  | "microsleep"
  | "off_road"
  | "phone"
  | "no_face"
  | "alarm"
  | "camera_lost"
  | "camera_restored"
  | "enroll_beep"
  | "monitoring_unavailable"
  | "monitoring_restored";

export interface Note {
  at: number; // seconds from the start of the sound
  freq: number; // Hz
  dur: number; // seconds
  wave: OscillatorType;
}

export interface Sound {
  kind: SoundKind;
  gain: number;
  notes: Note[];
}

/** L3 siren is repeated this often while the driver's eyes are still closed. */
export const ALARM_REPEAT_S = 1.5;

const GAIN: Record<Level, number> = { 0: 0, 1: 0.12, 2: 0.25, 3: 0.35 };

const seq = (freqs: number[], step: number, dur: number, wave: OscillatorType, start = 0): Note[] =>
  freqs.map((freq, i) => ({ at: start + i * step, freq, dur, wave }));

const KIND_OF_REASON: Partial<Record<Reason, SoundKind>> = {
  drowsy_score: "drowsy",
  blink_rate: "drowsy",
  trend: "trend",
  microsleep: "microsleep",
  off_road: "off_road",
  phone: "phone",
  no_face: "no_face",
};

function notesFor(kind: SoundKind, level: Level): Note[] {
  switch (kind) {
    case "drowsy":
      return level >= 2 ? seq([784, 659, 523], 0.28, 0.4, "sine") : seq([784, 587], 0.3, 0.45, "sine");
    case "trend":
      return seq([660], 0, 0.9, "sine");
    case "microsleep":
      return seq([523, 523], 0.35, 0.25, "sine");
    case "off_road":
      return [...seq([587, 880], 0.14, 0.14, "triangle"), ...seq([587, 880], 0.14, 0.14, "triangle", 0.4)];
    case "phone":
      return seq([1568, 1568, 1568], 0.12, 0.08, "square");
    case "no_face":
      return seq([330, 330, 330], 0.32, 0.22, "sawtooth");
    case "alarm":
      return seq([988, 1319, 988, 1319, 988, 1319], 0.16, 0.14, "square");
    case "camera_lost":
      return seq([440, 294, 196], 0.25, 0.3, "sawtooth");
    case "camera_restored":
      return seq([523, 784], 0.18, 0.25, "sine");
    case "monitoring_unavailable":
      return seq([330, 330, 330], 0.32, 0.22, "sawtooth");
    case "monitoring_restored":
      return seq([523, 784], 0.18, 0.25, "sine");
    case "enroll_beep":
      return seq([1047], 0, 0.25, "sine");
  }
}

/** Sound for an alert. reasons[0] is the reason that raised it (the alert manager puts it first). */
export function alertSound(level: Level, reasons: readonly Reason[]): Sound | null {
  if (level === 0) return null;
  const kind: SoundKind = level === 3 ? "alarm" : (KIND_OF_REASON[reasons[0]] ?? "drowsy");
  return { kind, gain: GAIN[level], notes: notesFor(kind, level) };
}

export type SystemSoundKind =
  | "camera_lost"
  | "camera_restored"
  | "enroll_beep"
  | "monitoring_unavailable"
  | "monitoring_restored";

export function systemSound(kind: SystemSoundKind): Sound {
  const loud = kind === "camera_lost" || kind === "monitoring_unavailable";
  return { kind, gain: loud ? GAIN[2] : GAIN[1], notes: notesFor(kind, 1) };
}

/** Spoken prompt (Vietnamese voice when the browser has one). Same user-gesture rule as sound. */
export function say(text: string): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "vi-VN";
  window.speechSynthesis.cancel(); // only the latest prompt matters
  window.speechSynthesis.speak(u);
}

let ctx: AudioContext | null = null;

export function unlock(): boolean {
  try {
    ctx ??= new AudioContext();
    void ctx.resume();
    return true;
  } catch {
    return false;
  }
}

function tone(at: number, note: Note, gain: number): void {
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.type = note.wave;
  osc.frequency.value = note.freq;
  amp.gain.setValueAtTime(0, at);
  amp.gain.linearRampToValueAtTime(gain, at + 0.02);
  amp.gain.exponentialRampToValueAtTime(0.001, at + note.dur);
  osc.connect(amp).connect(ctx.destination);
  osc.start(at);
  osc.stop(at + note.dur + 0.05);
}

export function play(sound: Sound | null): void {
  if (!ctx || !sound) return;
  const t = ctx.currentTime;
  for (const note of sound.notes) tone(t + note.at, note, sound.gain);
}

export function playAlert(level: Level, reasons: readonly Reason[]): void {
  play(alertSound(level, reasons));
}
