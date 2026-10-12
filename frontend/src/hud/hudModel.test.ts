import { describe, expect, it } from "vitest";
import type { EnrollStatus, HudEnrollment, HudSnapshot } from "../lib/types";
import {
  enrollCue,
  enrollReminder,
  hudCanLeave,
  monitoringStopped,
  orderedReasons,
  presenceUp,
  primaryReason,
  showConsentPanel,
  vehicleSignalLost,
  showEnrollPanel,
  systemState,
  urgentKey,
} from "./hudModel";

const snap = (connected = true): HudSnapshot => ({ connected, level: 0, reasons: [], alerts: [] });

describe("hudModel", () => {
  it("puts the most urgent reason first", () => {
    expect(primaryReason(["drowsy_score", "phone", "microsleep"])).toBe("microsleep");
    expect(primaryReason(["trend", "off_road"])).toBe("off_road");
    expect(primaryReason([])).toBeNull();
    expect(orderedReasons(["blink_rate", "phone", "drowsy_score"])).toEqual(["phone", "drowsy_score", "blink_rate"]);
  });

  it("keeps unknown reasons last instead of dropping them", () => {
    expect(orderedReasons(["camera_lost", "trend"])).toEqual(["trend", "camera_lost"]);
  });

  it("shows the driver panel only with a fresh, connected snapshot", () => {
    expect(systemState("ok", snap(), false, false)).toBeNull();
    expect(systemState("connecting", null, false, false)).toBe("connecting");
    expect(systemState("ok", snap(false), false, false)).toBe("connecting");
    expect(systemState("ok", snap(), true, false)).toBe("stale");
    expect(systemState("ok", snap(), true, true)).toBe("camera_lost");
    // the last snapshot goes stale when the link drops: say "link down", not "camera frozen"
    expect(systemState("down", snap(), true, false)).toBe("down");
  });

  it("shows 'monitoring unavailable' instead of an alert when the face is lost (FR-6)", () => {
    const off = { ...snap(), unavailable: true };
    expect(systemState("ok", off, false, false)).toBe("unavailable");
    expect(systemState("ok", off, false, true)).toBe("camera_lost"); // no camera explains more
    expect(systemState("ok", off, true, false)).toBe("stale");
  });

  it("shows the enrollment steps only when no alert is up", () => {
    const e = enroll("look_road");
    expect(showEnrollPanel(e, 0)).toBe(true);
    expect(showEnrollPanel(e, 1)).toBe(false); // an alert always wins
    expect(showEnrollPanel(enroll("done"), 0)).toBe(false);
    expect(showEnrollPanel(undefined, 0)).toBe(false);
  });

  it("shows a processing error and treats it, no data and no link as monitoring stopped (M28)", () => {
    const err = { ...snap(), processing_error: true };
    expect(systemState("ok", err, false, false)).toBe("error");
    expect(systemState("ok", err, false, true)).toBe("camera_lost"); // camera first
    expect(systemState("ok", snap(), false, false)).toBeNull();
    expect(monitoringStopped(systemState("ok", err, false, false))).toBe(true);
    expect(monitoringStopped(systemState("down", null, false, false))).toBe(true);
    expect(monitoringStopped(systemState("ok", snap(), true, false))).toBe(true); // stale
    expect(monitoringStopped(systemState("ok", { ...snap(), unavailable: true }, false, false))).toBe(false); // has its own sound
    expect(monitoringStopped(systemState("connecting", null, false, false))).toBe(false);
  });

  it("knows when the vehicle link was lost while driving (M26)", () => {
    const lost = { ...snap(), vehicle: { source: "sim", connected: false, speed_kmh: null, turn_signal: null, driving: true, signal_lost: true } };
    expect(vehicleSignalLost(lost)).toBe(true);
    expect(vehicleSignalLost({ ...lost, vehicle: { ...lost.vehicle, signal_lost: false } })).toBe(false);
    expect(vehicleSignalLost(snap())).toBe(false); // older agents send no flag
    expect(vehicleSignalLost(null)).toBe(false);
  });

  it("asks for consent before the steps, never over an alert", () => {
    expect(showConsentPanel(enroll("consent"), 0)).toBe(true);
    expect(showConsentPanel(enroll("consent"), 1)).toBe(false);
    expect(showConsentPanel(enroll("look_camera"), 0)).toBe(false);
    expect(showEnrollPanel(enroll("consent"), 0)).toBe(false); // not a step yet
    expect(enrollReminder(enroll("consent"))).toBeNull(); // the consent screen says it all
  });

  it("starts speaking only once the driver agreed", () => {
    expect(enrollCue(enroll("waiting"), enroll("consent"))).toEqual({ beep: false, say: null });
    expect(enrollCue(enroll("consent"), enroll("look_camera"))).toEqual({ beep: false, say: "Nhìn thẳng vào camera" });
  });

  it("reminds an unenrolled driver, quietly", () => {
    expect(enrollReminder(enroll("waiting"))).toMatch(/Dừng xe/);
    expect(enrollReminder(enroll("failed"))).toMatch(/lần dừng xe sau/);
    expect(enrollReminder(enroll("later"))).toMatch(/hỏi lại ở lần dừng xe sau/);
    expect(enrollReminder(enroll("done"))).toBeNull();
    expect(enrollReminder(enroll("off"))).toBeNull();
  });

  it("speaks each step and beeps when one ends", () => {
    expect(enrollCue(enroll("waiting"), enroll("look_camera"))).toEqual({ beep: false, say: "Nhìn thẳng vào camera" });
    expect(enrollCue(enroll("look_camera"), enroll("look_road"))).toEqual({ beep: true, say: "Nhìn ra đường phía trước" });
    expect(enrollCue(enroll("look_road"), enroll("close_eyes"))).toEqual({ beep: true, say: "Nhắm mắt lại" });
    // step 3 is done with the eyes shut: the beep is the signal to open them
    expect(enrollCue(enroll("close_eyes"), enroll("done"))).toEqual({ beep: true, say: "Làm quen xong" });
    expect(enrollCue(enroll("done"), enroll("done"))).toEqual({ beep: false, say: null });
    expect(enrollCue(undefined, enroll("done"))).toEqual({ beep: false, say: null }); // HUD opened mid-trip
  });

  it("says why a step is redone", () => {
    const cue = enrollCue(enroll("look_road", null, 0), enroll("look_road", "hold_still", 1));
    expect(cue).toEqual({ beep: false, say: "Giữ đầu yên. Nhìn ra đường phía trước" });
    expect(enrollCue(enroll("look_road", "hold_still", 1), enroll("look_road", "hold_still", 1)).say).toBeNull();
  });

  it("puts the unanswered alarm first and shows the presence question only while unavailable (M44)", () => {
    expect(primaryReason(["microsleep", "unresponsive"])).toBe("unresponsive");
    expect(primaryReason(["microsleep", "repeated_l3"])).toBe("repeated_l3");
    const asking: HudSnapshot = { ...snap(), unavailable: true, presence: { asking: true, remaining_s: 8, unanswered: false } };
    expect(presenceUp(systemState("ok", asking, false, false), asking)).toBe("asking");
    const silent: HudSnapshot = { ...asking, presence: { asking: false, remaining_s: 0, unanswered: true } };
    expect(presenceUp(systemState("ok", silent, false, false), silent)).toBe("unanswered");
    expect(presenceUp(systemState("ok", asking, false, true), asking)).toBeNull(); // camera lost explains more
    expect(presenceUp(systemState("ok", snap(), false, false), snap())).toBeNull();
    const old: HudSnapshot = { ...snap(), unavailable: true }; // an agent older than M44
    expect(presenceUp(systemState("ok", old, false, false), old)).toBeNull();
  });
});

function enroll(status: EnrollStatus, hint: HudEnrollment["hint"] = null, attempts = 0): HudEnrollment {
  return { status, progress: 0.5, hint, attempts };
}

describe("ways out of the HUD (M72)", () => {
  it("offers the demo and the Dashboard link only while no device is watched from this screen", () => {
    expect(hudCanLeave("connecting", null, false, false)).toBe(true); // nothing behind the screen yet
    expect(hudCanLeave("down", snap(), false, false)).toBe(true);
    expect(hudCanLeave("ok", { ...snap(), connected: false }, false, false)).toBe(true);
    expect(hudCanLeave("ok", snap(), false, false)).toBe(false); // a device is watching: one touch must not hide it
    expect(hudCanLeave("ok", { ...snap(), speed_kmh: 0 }, false, false)).toBe(false); // parked too: enrollment, alerts when it drives off
  });

  it("always leads back out of the demo, and never out of #/live", () => {
    expect(hudCanLeave("ok", snap(), true, false)).toBe(true); // "Về thiết bị thật"
    expect(hudCanLeave("connecting", null, false, true)).toBe(false); // leaving #/live stops the camera
    expect(hudCanLeave("down", null, true, true)).toBe(false);
  });
});

describe("what is pushed to the HUD at once (M50)", () => {
  const alert = (event_id: string) => ({ event_id, level: 2 as const, reasons: ["off_road" as const], at: 1, feedback: null });

  it("stays the same while only numbers move", () => {
    const a = { ...snap(), drowsy_score: 10, fps: 30, eyes_closed_s: 0 };
    const b = { ...snap(), drowsy_score: 35, fps: 24, eyes_closed_s: 0.4 };
    expect(urgentKey(a)).toBe(urgentKey(b));
  });

  it("changes with a new alert, another level, monitoring stopping, the presence question, an enrollment prompt", () => {
    const base = urgentKey(snap());
    const changed: HudSnapshot[] = [
      { ...snap(), alerts: [alert("e1")] },
      { ...snap(), level: 3 },
      { ...snap(), unavailable: true, unavailable_reason: "no_face" },
      { ...snap(), camera_lost: true },
      { ...snap(), processing_error: true },
      { ...snap(), presence: { asking: true, remaining_s: 10, unanswered: false } },
      { ...snap(), enrollment: { status: "look_road", progress: 0, hint: null, attempts: 0 } },
    ];
    const keys = changed.map(urgentKey);
    keys.forEach((k) => expect(k).not.toBe(base));
    expect(new Set(keys).size).toBe(keys.length);
    // the same L2 with a second alert (off_road, then phone) is pushed again
    expect(urgentKey({ ...snap(), level: 2, alerts: [alert("e2"), alert("e1")] })).not.toBe(urgentKey({ ...snap(), level: 2, alerts: [alert("e1")] }));
  });
});
