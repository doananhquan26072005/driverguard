/// <reference types="node" />
// The recorded Vietnamese voice (tools/make_voice.py): every alert has a line, the enrollment lines say
// exactly what the screen shows, and no line changed without its audio being made again.
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { ENROLL_HINTS, ENROLL_STEPS, ENROLL_TEXT } from "../lib/labels";
import type { HudEnrollment } from "../lib/types";
import { REASON_PRIORITY, alertVoiceKey, enrollVoiceKeys } from "./hudModel";
import LINES from "./voice-lines.json";

const VOICE_DIR = fileURLToPath(new URL("../../public/voice/", import.meta.url));
const lines: Record<string, string> = LINES;

describe("recorded voice", () => {
  it("has a line for every alert reason the HUD can lead with", () => {
    for (const r of REASON_PRIORITY.filter((r) => r !== "no_face")) expect(lines[`alert.${r}`], r).toBeTruthy();
  });

  it("says the enrollment words exactly as the screen shows them", () => {
    for (const [step, t] of Object.entries(ENROLL_STEPS)) expect(lines[`enroll.${step}`]).toBe(t.title);
    for (const [hint, t] of Object.entries(ENROLL_HINTS)) expect(lines[`hint.${hint}`]).toBe(t);
    expect(lines["enroll.done"]).toBe(ENROLL_TEXT.done);
    expect(lines["enroll.failed"]).toBe(ENROLL_TEXT.failed);
  });

  it("has an up-to-date audio file for every line (python tools/make_voice.py)", () => {
    const manifest = JSON.parse(readFileSync(VOICE_DIR + "manifest.json", "utf-8")) as Record<string, string>;
    for (const [key, text] of Object.entries(lines)) {
      expect(existsSync(`${VOICE_DIR}${key}.wav`), `${key}.wav`).toBe(true);
      expect(manifest[key], `${key} changed: run tools/make_voice.py`).toBe(createHash("sha1").update(text, "utf8").digest("hex").slice(0, 12));
    }
  });

  it("picks the line of the most urgent reason", () => {
    expect(alertVoiceKey(["drowsy_score", "microsleep"])).toBe("alert.microsleep");
    expect(alertVoiceKey(["off_road", "phone"])).toBe("alert.phone");
    expect(alertVoiceKey([])).toBeNull();
  });

  it("speaks the hint before the step it repeats, and the end of enrollment", () => {
    const e = (status: HudEnrollment["status"], attempts = 0, hint: HudEnrollment["hint"] = null): HudEnrollment => ({ status, progress: 0, hint, attempts });
    expect(enrollVoiceKeys(e("consent"), e("look_camera"))).toEqual(["enroll.look_camera"]);
    expect(enrollVoiceKeys(e("look_road"), e("look_road", 1, "hold_still"))).toEqual(["hint.hold_still", "enroll.look_road"]);
    expect(enrollVoiceKeys(e("close_eyes"), e("done"))).toEqual(["enroll.done"]);
    expect(enrollVoiceKeys(e("look_road"), e("failed"))).toEqual(["enroll.failed"]);
    expect(enrollVoiceKeys(e("look_road"), e("look_road"))).toEqual([]);
  });
});
