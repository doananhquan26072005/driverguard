import { describe, expect, it } from "vitest";
import { LoopWatchdog, type CameraTrack } from "./watchdog";

const TIMEOUT = 3000; // capture.frame_timeout_s
const RECONNECT = 2000; // capture.reconnect_interval_s

/** Frames every 33 ms from the browser's callback up to `untilMs`. */
function frames(w: LoopWatchdog, fromMs: number, untilMs: number) {
  for (let t = fromMs; t <= untilMs; t += 33) w.frame(t, false);
}

/** One look per second from `fromMs` to `untilMs`; the verdict of each look. */
function looks(w: LoopWatchdog, fromMs: number, untilMs: number, track: CameraTrack = "live", visible = true) {
  const out = [];
  for (let t = fromMs; t <= untilMs; t += 1000) out.push({ t, ...w.check(t, track, visible) });
  return out;
}

describe("LoopWatchdog", () => {
  it("leaves a loop that gets frames alone", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    frames(w, 0, 10_000);
    expect(w.check(10_500, "live", true)).toEqual({ pull: false, lost: false, reopen: 0 });
  });

  it("pulls frames once the callback has been quiet for the frame timeout, not before", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    frames(w, 0, 1000);
    expect(w.check(3900, "live", true).pull).toBe(false);
    expect(w.check(4100, "live", true)).toEqual({ pull: true, lost: false, reopen: 0 });
  });

  it("keeps pulling while pulled frames come, and stops when the callback is heard again", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    expect(w.check(3000, "live", true).pull).toBe(true);
    for (let t = 3033; t < 20_000; t += 33) w.frame(t, true);
    expect(w.check(20_000, "live", true)).toEqual({ pull: true, lost: false, reopen: 0 });
    w.frame(20_010, false);
    expect(w.check(20_100, "live", true)).toEqual({ pull: false, lost: false, reopen: 0 });
  });

  it("calls the camera lost when pulling brings no frame either, and asks for it again at the reconnect interval", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    const seen = looks(w, 1000, 12_000);
    expect(seen.find((v) => v.pull)?.t).toBe(3000);
    expect(seen.find((v) => v.lost)?.t).toBe(6000);
    expect(seen.filter((v) => v.reopen).map((v) => [v.t, v.reopen])).toEqual([
      [6000, 1],
      [8000, 2],
      [10_000, 3],
      [12_000, 4],
    ]);
  });

  it("acts on an ended track at once, without waiting for the frame timeout", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    frames(w, 0, 1000);
    expect(w.check(1010, "ended", true)).toEqual({ pull: false, lost: true, reopen: 1 });
    expect(w.check(1500, "ended", true).reopen).toBe(0); // one attempt per reconnect interval
    expect(w.check(3010, "ended", true).reopen).toBe(2);
  });

  it("treats a muted track as lost only after the frame timeout", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    frames(w, 0, 1000);
    expect(w.check(2000, "muted", true).lost).toBe(false);
    expect(w.check(4000, "muted", true)).toEqual({ pull: false, lost: true, reopen: 1 });
  });

  it("is restored by the first frame, and counts attempts from one again the next time", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    expect(w.check(0, "ended", true).reopen).toBe(1);
    expect(w.check(2000, "ended", true).reopen).toBe(2);
    w.frame(2500, false);
    expect(w.check(2600, "live", true)).toEqual({ pull: false, lost: false, reopen: 0 });
    expect(w.check(60_000, "ended", true).reopen).toBe(1);
  });

  it("gives a reopened camera the frame timeout before asking again", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    expect(w.check(0, "ended", true).reopen).toBe(1);
    w.reopened(500); // getUserMedia answered, no frame yet
    expect(looks(w, 1000, 3000).every((v) => v.lost && v.reopen === 0)).toBe(true);
    expect(w.check(3500, "live", true).reopen).toBe(2);
  });

  it("does not pull in a background tab, and still reopens an ended camera there", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    expect(looks(w, 1000, 30_000, "live", false).every((v) => !v.pull && !v.lost && !v.reopen)).toBe(true);
    expect(w.check(31_000, "live", true).pull).toBe(true); // back in front: pulled at the next look
    expect(w.check(32_000, "ended", false)).toEqual({ pull: false, lost: true, reopen: 1 });
  });

  it("never reopens when the reconnect interval is 0", () => {
    const w = new LoopWatchdog(TIMEOUT, 0, 0);
    expect(looks(w, 0, 20_000, "ended").every((v) => v.lost && v.reopen === 0)).toBe(true);
  });
  // M83: frames arrive, the image in them does not change
  /** Frames every 33 ms that all show the same image. */
  function stills(w: LoopWatchdog, fromMs: number, untilMs: number) {
    const shown = [];
    for (let t = fromMs; t <= untilMs; t += 33) {
      w.frame(t, false);
      shown.push(w.image(t, false));
    }
    return shown;
  }

  it("calls a camera that repeats one image lost after the frame timeout, and asks for it again", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    for (let t = 0; t <= 5000; t += 33) {
      w.frame(t, false);
      expect(w.image(t, true)).toBe(true);
    }
    expect(stills(w, 5033, 7900).every(Boolean)).toBe(true); // under 3 s of the same image: a still scene
    expect(w.check(7900, "live", true)).toEqual({ pull: false, lost: false, reopen: 0 });
    expect(stills(w, 7933, 9000).at(-1)).toBe(false); // not a view of the driver: the frame is not used
    expect(w.still).toBe(true);
    expect(w.check(9000, "live", true)).toEqual({ pull: false, lost: true, reopen: 1 });
    stills(w, 9033, 11_000); // frames go on arriving: still lost, the attempts are not forgotten
    expect(w.check(11_000, "live", true)).toEqual({ pull: false, lost: true, reopen: 2 });
  });

  it("takes the camera back only on an image that differs", () => {
    const w = new LoopWatchdog(TIMEOUT, RECONNECT, 0);
    stills(w, 0, 4000);
    expect(w.check(4000, "live", true).lost).toBe(true);
    w.reopened(4100); // the reopened camera hands over the same image
    stills(w, 4133, 5000);
    expect(w.check(5000, "live", true).lost).toBe(true);
    w.frame(5033, false);
    expect(w.image(5033, true)).toBe(true);
    expect(w.still).toBe(false);
    expect(w.check(5100, "live", true)).toEqual({ pull: false, lost: false, reopen: 0 });
    expect(stills(w, 5133, 8000).every(Boolean)).toBe(true); // the 3 s start again from the last change
  });
});
