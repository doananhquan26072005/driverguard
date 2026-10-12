// Alert sounds with WebAudio (no audio files). Sound is always on: armAudio() creates the audio
// context as the HUD opens and resumes it on the first touch / key anywhere (browsers only allow
// sound after a user gesture; the APK can allow it from the start). While it is still blocked the
// HUD asks the driver to touch the screen.
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
// - vehicle signal lost while driving / back (M26): two falling triangle notes, twice / rising two notes
// - monitoring stopped (M28: HUD gets no data / no link / frames failing): three long falling buzzes
// - driver enrollment: one short clear beep when a step ends ("open your eyes" after step 3)
// The level sets the volume. alertSound() is pure (tested); play() does the WebAudio part.
import type { Level, Reason } from "../lib/types";
import { HUD_DEFAULTS } from "../lib/defaults";
import VOICE_LINES from "./voice-lines.json";

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
  | "monitoring_restored"
  | "vehicle_signal_lost"
  | "vehicle_signal_restored"
  | "monitoring_stopped"
  | "presence";

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

// Loudness by level (thresholds.yaml hud.gain): the build's own until the agent's state brings its.
let gain: readonly number[] = HUD_DEFAULTS.gain;

/** The agent's hud.gain (HudSnapshot.display.gain), by level 0-3. */
export function setGain(byLevel: readonly number[]): void {
  gain = byLevel;
}

const seq = (freqs: number[], step: number, dur: number, wave: OscillatorType, start = 0): Note[] =>
  freqs.map((freq, i) => ({ at: start + i * step, freq, dur, wave }));

const KIND_OF_REASON: Partial<Record<Reason, SoundKind>> = {
  drowsy_score: "drowsy",
  blink_rate: "drowsy",
  trend: "trend",
  microsleep: "microsleep",
  unresponsive: "microsleep",
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
    case "vehicle_signal_lost":
      return [...seq([660, 440], 0.22, 0.2, "triangle"), ...seq([660, 440], 0.22, 0.2, "triangle", 0.6)];
    case "vehicle_signal_restored":
      return seq([440, 660], 0.18, 0.25, "sine");
    case "monitoring_stopped":
      return seq([587, 440, 294], 0.32, 0.3, "sawtooth");
    case "presence": // a question: two rising pairs
      return [...seq([523, 784], 0.16, 0.16, "triangle"), ...seq([523, 784], 0.16, 0.16, "triangle", 0.5)];
  }
}

/** Sound for an alert. reasons[0] is the reason that raised it (the alert manager puts it first). */
export function alertSound(level: Level, reasons: readonly Reason[]): Sound | null {
  if (level === 0) return null;
  const kind: SoundKind = level === 3 ? "alarm" : (KIND_OF_REASON[reasons[0]] ?? "drowsy");
  return { kind, gain: gain[level], notes: notesFor(kind, level) };
}

export type SystemSoundKind =
  | "camera_lost"
  | "camera_restored"
  | "enroll_beep"
  | "monitoring_unavailable"
  | "monitoring_restored"
  | "vehicle_signal_lost"
  | "vehicle_signal_restored"
  | "monitoring_stopped"
  | "presence";

export function systemSound(kind: SystemSoundKind): Sound {
  const loud =
    kind === "camera_lost" || kind === "monitoring_unavailable" || kind === "vehicle_signal_lost" || kind === "monitoring_stopped" || kind === "presence";
  return { kind, gain: loud ? gain[2] : gain[1], notes: notesFor(kind, 1) };
}

/** The Vietnamese voice to speak with, or null. Setting only `lang` is not enough: a browser without a
 *  Vietnamese voice reads the Vietnamese words with its default (English) voice, which nobody
 *  understands. Prefers vi-VN, then any vi, a local voice before a network one (the car may be offline). */
export function pickVietnameseVoice<V extends { lang: string; localService: boolean }>(voices: readonly V[]): V | null {
  const vi = voices.filter((v) => v.lang.toLowerCase().replace("_", "-").startsWith("vi"));
  const rank = (v: V) => (v.lang.toLowerCase().replace("_", "-") === "vi-vn" ? 0 : 2) + (v.localService ? 0 : 1);
  return [...vi].sort((a, b) => rank(a) - rank(b))[0] ?? null;
}

let viVoice: SpeechSynthesisVoice | null = null;
let voicesKnown = false; // the browser has listed its voices (Chrome lists them asynchronously)
const voiceListeners = new Set<() => void>();

function loadVoices(): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  const list = window.speechSynthesis.getVoices();
  if (list.length) {
    viVoice = pickVietnameseVoice(list);
    voicesKnown = true;
    voiceListeners.forEach((f) => f());
  }
}
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  loadVoices();
  window.speechSynthesis.addEventListener?.("voiceschanged", loadVoices);
}

/** null while the browser has not listed its voices yet; then whether a Vietnamese one exists. */
export function hasVietnameseVoice(): boolean | null {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return false;
  if (!voicesKnown) loadVoices(); // Chrome may list them later without a voiceschanged event
  return voicesKnown ? viVoice != null : null;
}

/** Called once the voices are known (the setup / enrollment screens show a hint when none is Vietnamese). */
export function onVoices(listener: () => void): () => void {
  voiceListeners.add(listener);
  return () => voiceListeners.delete(listener);
}

/** Spoken prompt, only with a Vietnamese voice (never Vietnamese words in an English voice). Without one
 *  the words stay on screen and the beeps play. Same user-gesture rule as sound. */
export function say(text: string): void {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;
  if (!viVoice) loadVoices();
  if (!viVoice) return;
  const u = new SpeechSynthesisUtterance(text);
  u.voice = viVoice;
  u.lang = viVoice.lang;
  window.speechSynthesis.cancel(); // only the latest prompt matters
  window.speechSynthesis.speak(u);
}

/** What the driver can do when no Vietnamese voice is installed. */
export const NO_VIETNAMESE_VOICE_TEXT =
  "Máy này chưa có giọng đọc tiếng Việt: hướng dẫn chỉ hiện bằng chữ và tiếng bíp. Cài giọng: Cài đặt Windows › Thời gian và ngôn ngữ › Ngôn ngữ › thêm Tiếng Việt (chọn Giọng nói), hoặc mở trang bằng Microsoft Edge.";

let ctx: AudioContext | null = null;

/** Sound is playing (the audio context runs). False until the browser allows it. */
export function audioOn(): boolean {
  return ctx?.state === "running";
}

/** Resume the audio context; call it from a touch / click (also done by armAudio's listeners). */
export function unlock(): boolean {
  try {
    ctx ??= new AudioContext();
    void ctx.resume().catch(() => undefined);
    return true;
  } catch {
    return false;
  }
}

const GESTURES = ["pointerdown", "touchstart", "keydown"] as const;

/** Sound on from the start: create the audio context now, resume it on the first gesture anywhere,
 *  and report every change (running / blocked). Returns the clean-up. */
export function armAudio(onChange: (on: boolean) => void): () => void {
  if (typeof window === "undefined" || !unlock() || !ctx) {
    onChange(false);
    return () => undefined;
  }
  const audio = ctx;
  const report = () => onChange(audio.state === "running");
  const onGesture = () => {
    unlock();
    report();
  };
  audio.addEventListener("statechange", report);
  GESTURES.forEach((e) => window.addEventListener(e, onGesture, { capture: true, passive: true }));
  report();
  return () => {
    audio.removeEventListener("statechange", report);
    GESTURES.forEach((e) => window.removeEventListener(e, onGesture, { capture: true }));
  };
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
  // Not while blocked: notes scheduled on a suspended context would all sound at once on resume.
  if (!ctx || ctx.state !== "running" || !sound) return;
  const t = ctx.currentTime;
  for (const note of sound.notes) tone(t + note.at, note, sound.gain);
}

export function playAlert(level: Level, reasons: readonly Reason[]): void {
  play(alertSound(level, reasons));
}

// ------------------------------------------------------------------ recorded Vietnamese voice
// Every spoken line is a file made once by tools/make_voice.py (voice vi-VN-NamMinhNeural) from
// hud/voice-lines.json, so the HUD speaks Vietnamese on any computer and offline. A missing file falls
// back to the browser's Vietnamese voice (say), never to an English one.

export type VoiceKey = keyof typeof VOICE_LINES;
export const VOICE_TEXT: Record<string, string> = VOICE_LINES;

let voiceQueue: VoiceKey[] = [];
let voicePlaying: HTMLAudioElement | null = null;

function playNextLine(): void {
  const key = voiceQueue.shift();
  if (!key) {
    voicePlaying = null;
    return;
  }
  const audio = new Audio(`${import.meta.env.BASE_URL}voice/${key}.mp3`);
  voicePlaying = audio;
  audio.onended = playNextLine;
  audio.onerror = () => {
    say(VOICE_TEXT[key]); // no file: the browser's Vietnamese voice if it has one, else silent
    playNextLine();
  };
  audio.play().catch(() => {
    voicePlaying = null; // sound still blocked by the browser: the strip on screen asks for a touch
    voiceQueue = [];
  });
}

/** Speak recorded lines in order, cutting what was being said (only the latest message matters). */
export function speak(...keys: (VoiceKey | null | undefined)[]): void {
  if (typeof window === "undefined" || typeof Audio === "undefined") return;
  voicePlaying?.pause();
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
  voiceQueue = keys.filter((k): k is VoiceKey => !!k && k in VOICE_TEXT);
  playNextLine();
}
