// Alert sounds with WebAudio (no audio files). Browsers only allow sound after a user
// gesture, so the HUD has a "Bật âm thanh" button that calls unlock().
import type { Level } from "../lib/types";

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

function tone(at: number, freq: number, dur: number, gain = 0.2): void {
  if (!ctx) return;
  const osc = ctx.createOscillator();
  const amp = ctx.createGain();
  osc.frequency.value = freq;
  amp.gain.setValueAtTime(0, at);
  amp.gain.linearRampToValueAtTime(gain, at + 0.02);
  amp.gain.exponentialRampToValueAtTime(0.001, at + dur);
  osc.connect(amp).connect(ctx.destination);
  osc.start(at);
  osc.stop(at + dur + 0.05);
}

/** L1: one soft chime, L2: two tones, L3: urgent triple beep. */
export function playAlert(level: Level): void {
  if (!ctx || level === 0) return;
  const t = ctx.currentTime;
  if (level === 1) tone(t, 880, 0.4, 0.12);
  if (level === 2) {
    tone(t, 740, 0.25);
    tone(t + 0.3, 988, 0.35);
  }
  if (level === 3) for (let i = 0; i < 3; i++) tone(t + i * 0.22, 1175, 0.16, 0.3);
}
