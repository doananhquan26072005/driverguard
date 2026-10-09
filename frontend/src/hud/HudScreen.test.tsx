// @vitest-environment jsdom
// What the driver hears (M88, audit A4 M10): HudScreen's effects, mounted for real, against a source
// that hands over the states the test wants and a clock the test moves. chime.ts is replaced by a
// record of what would have sounded; HudView by a record of its props (it only draws).
import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HUD_DEFAULTS } from "../lib/defaults";
import type { HudAlert, HudSnapshot, Level, Reason } from "../lib/types";
import type { HudSource } from "./edge";
import HudScreen from "./HudScreen";

const chime = vi.hoisted(() => ({
  allowed: true, // false: the browser blocks sound until a touch
  change: null as ((on: boolean) => void) | null,
  play: vi.fn(),
  playAlert: vi.fn(),
  speak: vi.fn(),
  setGain: vi.fn(),
}));
vi.mock("./chime", () => ({
  armAudio: (onChange: (on: boolean) => void) => {
    chime.change = onChange;
    onChange(chime.allowed);
    return () => undefined;
  },
  play: chime.play,
  playAlert: chime.playAlert,
  speak: chime.speak,
  setGain: chime.setGain,
  systemSound: (kind: string) => kind,
  unlock: () => true,
}));

interface ViewProps {
  demo: boolean;
  onToggleDemo?: () => void;
}
const view = vi.hoisted(() => ({ props: null as unknown }));
vi.mock("./HudView", () => ({ default: (props: unknown) => ((view.props = props), null) }));
vi.mock("./TripSummaryView", () => ({ default: () => null }));
const shown = () => view.props as ViewProps;

const POLL_MS = HUD_DEFAULTS.poll_s * 1000;
const VOICE_MS = HUD_DEFAULTS.chime_to_voice_s * 1000;
const ALARM_MS = HUD_DEFAULTS.alarm_repeat_s * 1000;
const PRESENCE_MS = HUD_DEFAULTS.presence_repeat_s * 1000;

const snap = (more: Partial<HudSnapshot> = {}): HudSnapshot => ({ connected: true, level: 0, reasons: [], alerts: [], ...more });
const alert = (id: string, level: Level, ...reasons: Reason[]): HudAlert => ({ event_id: id, level, reasons, at: Date.now() / 1000, feedback: null });
const alerted = (id: string, level: Level, reason: Reason, more: Partial<HudSnapshot> = {}) =>
  snap({ level, reasons: [reason], alerts: [alert(id, level, reason)], ...more });

/** A HUD source the test drives. inPage: #/live (it has the camera and can push), else the device's HUD server. */
function fakeSource(first: HudSnapshot | null, inPage = true) {
  let current = first;
  const listeners = new Set<(s: HudSnapshot) => void>();
  const source: HudSource = {
    address: "test",
    state: vi.fn(async () => {
      if (!current) throw new Error("offline");
      return current;
    }),
    falseAlarm: vi.fn(async () => "recorded" as const),
    ...(inPage ? { subscribe: (l) => (listeners.add(l), () => void listeners.delete(l)), cameraStream: () => null } : {}),
  };
  return {
    source,
    listeners,
    /** What the next poll will read. */
    set: (next: HudSnapshot | null) => void (current = next),
    /** The agent hands the state over in the frame it changed (M50). */
    push: (next: HudSnapshot) => act(async () => ((current = next), listeners.forEach((l) => l(next)))),
  };
}

let root: Root;
async function mount(source: HudSource) {
  root = createRoot(document.body.appendChild(document.createElement("div")));
  await act(async () => root.render(<HudScreen source={source} />));
  await wait(0);
}
const wait = (ms: number) => act(async () => void (await vi.advanceTimersByTimeAsync(ms)));
const sounds = () => chime.play.mock.calls.map((c) => c[0] as string);
const said = () => chime.speak.mock.calls.map((c) => c.join(" + "));
const sirens = () => chime.playAlert.mock.calls.filter((c) => c[0] === 3 && (c[1] as Reason[]).length === 0).length;

beforeEach(() => {
  vi.useFakeTimers();
  (globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;
  chime.allowed = true;
  [chime.play, chime.playAlert, chime.speak, chime.setGain].forEach((f) => f.mockClear());
});

afterEach(async () => {
  await act(async () => root.unmount());
  document.body.innerHTML = "";
  vi.useRealTimers();
});

describe("alerts", () => {
  it("a pushed alert sounds in the frame it comes, its spoken line follows the chime, and it sounds once", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    expect(chime.playAlert).not.toHaveBeenCalled();
    await hud.push(alerted("e1", 2, "off_road"));
    expect(chime.playAlert.mock.calls).toEqual([[2, ["off_road"]]]); // no poll in between
    await wait(VOICE_MS - 1);
    expect(chime.speak).not.toHaveBeenCalled();
    await wait(1);
    expect(said()).toEqual(["alert.off_road"]);
    await wait(10 * POLL_MS); // polled again and again: the same alert
    expect(chime.playAlert).toHaveBeenCalledTimes(1);
    expect(chime.speak).toHaveBeenCalledTimes(1);
  });

  it("a source that cannot push (the device's HUD) is heard at the next poll", async () => {
    const hud = fakeSource(snap(), false);
    await mount(hud.source);
    hud.set(alerted("e1", 1, "drowsy_score"));
    await wait(POLL_MS - 1);
    expect(chime.playAlert).not.toHaveBeenCalled();
    await wait(1);
    expect(chime.playAlert.mock.calls).toEqual([[1, ["drowsy_score"]]]);
  });

  it("each new alert sounds, by its own level and reasons, the newest of the list", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    const first = alert("e1", 1, "drowsy_score");
    await hud.push(snap({ level: 1, reasons: ["drowsy_score"], alerts: [first] }));
    await hud.push(snap({ level: 2, reasons: ["phone"], alerts: [alert("e2", 2, "phone", "off_road"), first] }));
    expect(chime.playAlert.mock.calls).toEqual([
      [1, ["drowsy_score"]],
      [2, ["phone", "off_road"]],
    ]);
    await wait(VOICE_MS);
    expect(said()).toEqual(["alert.drowsy_score", "alert.phone"]);
  });

  it("a HUD opened on a trip with several past alerts does not sound them", async () => {
    const hud = fakeSource(snap({ alerts: [alert("e2", 2, "phone"), alert("e1", 1, "drowsy_score")] }));
    await mount(hud.source);
    await wait(VOICE_MS + POLL_MS);
    expect(chime.playAlert).not.toHaveBeenCalled();
    expect(chime.speak).not.toHaveBeenCalled();
    await hud.push(snap({ alerts: [alert("e3", 2, "off_road"), alert("e2", 2, "phone"), alert("e1", 1, "drowsy_score")] }));
    expect(chime.playAlert.mock.calls).toEqual([[2, ["off_road"]]]);
  });

  it("a HUD opened on a trip with exactly one past alert does not sound it either (M100)", async () => {
    // Before: only a list of two or more was taken for history, so a single old alert rang again.
    const hud = fakeSource(snap({ alerts: [alert("e1", 2, "phone")] }));
    await mount(hud.source);
    await wait(VOICE_MS + POLL_MS);
    expect(chime.playAlert).not.toHaveBeenCalled();
    expect(chime.speak).not.toHaveBeenCalled();
    await hud.push(snap({ level: 2, reasons: ["off_road"], alerts: [alert("e2", 2, "off_road"), alert("e1", 2, "phone")] }));
    expect(chime.playAlert.mock.calls).toEqual([[2, ["off_road"]]]); // the next one is new, and is heard
  });

  it("the volume per level comes from the agent's state, and from the build before the first one", async () => {
    const hud = fakeSource(null);
    await mount(hud.source);
    expect(chime.setGain).toHaveBeenLastCalledWith(HUD_DEFAULTS.gain);
    await hud.push(snap({ display: { ...HUD_DEFAULTS, gain: [0, 0.2, 0.4, 0.6] } }));
    expect(chime.setGain).toHaveBeenLastCalledWith([0, 0.2, 0.4, 0.6]);
  });
});

describe("the L3 siren", () => {
  it("is repeated every alarm_repeat_s with its order while the eyes stay closed, and stops when they open", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(alerted("e1", 3, "microsleep", { eyes_closed_s: 1.6 }));
    expect(chime.playAlert.mock.calls).toEqual([[3, ["microsleep"]]]);
    await wait(3 * ALARM_MS + VOICE_MS);
    expect(sirens()).toBe(3);
    expect(said()).toEqual(Array(4).fill("alert.microsleep"));

    await hud.push(alerted("e1", 3, "microsleep", { eyes_closed_s: 0 })); // L3 still held, eyes open
    await wait(4 * ALARM_MS);
    expect(sirens()).toBe(3);
  });

  it("is not repeated for an L3 whose eyes are open, nor under a lost camera or stale data", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(alerted("e1", 3, "unresponsive", { eyes_closed_s: 0 }));
    await wait(3 * ALARM_MS);
    expect(sirens()).toBe(0);
    await hud.push(alerted("e1", 3, "microsleep", { eyes_closed_s: 2, camera_lost: true }));
    await wait(3 * ALARM_MS);
    expect(sirens()).toBe(0);
  });
});

describe("monitoring stops and comes back", () => {
  it("camera lost / back: its own sound and line, each once", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(snap({ camera_lost: true }));
    await wait(VOICE_MS);
    expect(sounds()).toEqual(["camera_lost"]);
    expect(said()).toEqual(["sys.camera_lost"]);
    await wait(10 * POLL_MS);
    await hud.push(snap());
    await wait(VOICE_MS);
    expect(sounds()).toEqual(["camera_lost", "camera_restored"]);
    expect(said()).toEqual(["sys.camera_lost", "sys.camera_restored"]);
  });

  it("face lost while moving (unavailable) / back", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(snap({ unavailable: true, unavailable_reason: "no_face" }));
    await hud.push(snap());
    await wait(VOICE_MS);
    expect(sounds()).toEqual(["monitoring_unavailable", "monitoring_restored"]);
    expect(said()).toEqual(["sys.unavailable", "sys.restored"]);
  });

  it("frames keep failing (processing error): the loud stop sound, then restored", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(snap({ processing_error: true }));
    await hud.push(snap());
    await wait(VOICE_MS);
    expect(sounds()).toEqual(["monitoring_stopped", "monitoring_restored"]);
    expect(said()).toEqual(["sys.stopped", "sys.restored"]);
  });

  it("no new state for stale_s (the loop stopped): the stop sound once, restored with the next state", async () => {
    const hud = fakeSource(snap({ updated_at: Date.now() / 1000 }));
    await mount(hud.source);
    await wait(HUD_DEFAULTS.stale_s * 1000 - POLL_MS);
    expect(sounds()).toEqual([]);
    await wait(2 * POLL_MS);
    expect(sounds()).toEqual(["monitoring_stopped"]);
    await wait(20 * POLL_MS);
    expect(sounds()).toEqual(["monitoring_stopped"]);
    await hud.push(snap({ updated_at: Date.now() / 1000 }));
    expect(sounds()).toEqual(["monitoring_stopped", "monitoring_restored"]);
  });

  it("the link to the device goes down after link_down_failures polls without an answer", async () => {
    const hud = fakeSource(snap(), false);
    await mount(hud.source);
    hud.set(null);
    await wait((HUD_DEFAULTS.link_down_failures - 1) * POLL_MS);
    expect(sounds()).toEqual([]);
    await wait(POLL_MS);
    expect(sounds()).toEqual(["monitoring_stopped"]);
    hud.set(snap());
    await wait(POLL_MS);
    expect(sounds()).toEqual(["monitoring_stopped", "monitoring_restored"]);
  });

  it("not after the trip ended: a loop that stopped on purpose is silent", async () => {
    const hud = fakeSource(snap({ updated_at: Date.now() / 1000, trip_ended: true }), false);
    await mount(hud.source);
    await wait(HUD_DEFAULTS.stale_s * 1000 + 5 * POLL_MS);
    expect(sounds()).toEqual([]);
  });

  it("the vehicle signal lost / back", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(snap({ vehicle: { signal_lost: true } as HudSnapshot["vehicle"] }));
    await hud.push(snap({ vehicle: { signal_lost: false } as HudSnapshot["vehicle"] }));
    await wait(VOICE_MS);
    expect(sounds()).toEqual(["vehicle_signal_lost", "vehicle_signal_restored"]);
    expect(said()).toEqual(["sys.vehicle_lost", "sys.vehicle_restored"]);
  });
});

describe('"Bạn còn ở đó không?"', () => {
  const away = (presence: HudSnapshot["presence"]) => snap({ unavailable: true, unavailable_reason: "no_face", presence });

  it("the question rings at once and every presence_repeat_s; unanswered, the L3 siren takes over; it ends with the face", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(away({ asking: true, remaining_s: 8, unanswered: false }));
    await wait(2 * PRESENCE_MS + VOICE_MS);
    expect(sounds().filter((s) => s === "presence").length).toBe(3);
    expect(said().filter((s) => s === "sys.presence").length).toBe(3);
    expect(sirens()).toBe(0);

    await hud.push(away({ asking: false, remaining_s: 0, unanswered: true }));
    await wait(2 * PRESENCE_MS);
    expect(sirens()).toBe(3);
    expect(sounds().filter((s) => s === "presence").length).toBe(3);

    await hud.push(snap());
    await wait(3 * PRESENCE_MS);
    expect(sirens()).toBe(3);
    expect(sounds().at(-1)).toBe("monitoring_restored");
  });

  it("is not rung over a lost camera", async () => {
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push({ ...away({ asking: true, remaining_s: 8, unanswered: false }), camera_lost: true });
    await wait(2 * PRESENCE_MS);
    expect(sounds()).toEqual(["camera_lost"]);
  });
});

describe("enrollment", () => {
  it("a new step is spoken; the end of a step beeps first; done is said once", async () => {
    const step = (status: string, attempts = 0, hint: string | null = null) =>
      snap({ enrollment: { status, progress: 0, hint, attempts } as HudSnapshot["enrollment"] });
    const hud = fakeSource(step("consent"));
    await mount(hud.source);
    await hud.push(step("look_camera"));
    expect(said()).toEqual(["enroll.look_camera"]); // the first step: no beep, said at once
    expect(sounds()).toEqual([]);
    await hud.push(step("look_road"));
    expect(sounds()).toEqual(["enroll_beep"]);
    await wait(VOICE_MS);
    expect(said()).toEqual(["enroll.look_camera", "enroll.look_road"]);
    await hud.push(step("look_road", 1, "face_not_found")); // the step is redone: what to fix, then the step
    expect(said().at(-1)).toBe("hint.face_not_found + enroll.look_road");
    await hud.push(step("done", 1));
    await wait(VOICE_MS + 5 * POLL_MS);
    expect(sounds()).toEqual(["enroll_beep", "enroll_beep"]);
    expect(said().filter((s) => s === "enroll.done").length).toBe(1);
  });
});

describe("while the browser blocks sound", () => {
  it("nothing sounds; with the first touch, what still holds is sounded once, and what repeats starts (M100)", async () => {
    // Before: the alert and the lost signal that came while blocked were never sounded.
    chime.allowed = false;
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(alerted("e1", 3, "microsleep", { eyes_closed_s: 2 }));
    await hud.push(alerted("e1", 3, "microsleep", { eyes_closed_s: 2.5, vehicle: { signal_lost: true } as HudSnapshot["vehicle"] }));
    await wait(3 * ALARM_MS);
    expect(chime.playAlert).not.toHaveBeenCalled();
    expect(chime.play).not.toHaveBeenCalled();
    expect(chime.speak).not.toHaveBeenCalled();

    await act(async () => chime.change?.(true)); // the first touch
    expect(chime.playAlert.mock.calls).toEqual([[3, ["microsleep"]]]); // the alert that is still up
    expect(sounds()).toEqual(["vehicle_signal_lost"]);
    await wait(ALARM_MS);
    expect(sirens()).toBe(1); // the eyes are still closed: the siren goes on from here
    await wait(10 * POLL_MS);
    expect(chime.playAlert.mock.calls.filter((c) => (c[1] as Reason[]).length > 0)).toHaveLength(1); // the alert itself: once
    expect(sounds()).toEqual(["vehicle_signal_lost"]);
  });

  it("an alert that was over before the first touch is not sounded late", async () => {
    chime.allowed = false;
    const hud = fakeSource(snap());
    await mount(hud.source);
    const old = alert("e1", 2, "off_road");
    await hud.push(snap({ level: 2, reasons: ["off_road"], alerts: [old] }));
    await hud.push(snap({ level: 0, reasons: [], alerts: [old] })); // the driver looked back at the road
    await act(async () => chime.change?.(true));
    await wait(VOICE_MS + POLL_MS);
    expect(chime.playAlert).not.toHaveBeenCalled();
    expect(chime.speak).not.toHaveBeenCalled();
  });

  it("of two alerts that came while blocked, only the newest is sounded", async () => {
    chime.allowed = false;
    const hud = fakeSource(snap());
    await mount(hud.source);
    const first = alert("e1", 1, "drowsy_score");
    await hud.push(snap({ level: 1, reasons: ["drowsy_score"], alerts: [first] }));
    await hud.push(snap({ level: 2, reasons: ["phone"], alerts: [alert("e2", 2, "phone"), first] }));
    await act(async () => chime.change?.(true));
    expect(chime.playAlert.mock.calls).toEqual([[2, ["phone"]]]);
  });

  it("monitoring that stopped while blocked is told with the first touch; what came back meanwhile is not", async () => {
    chime.allowed = false;
    const hud = fakeSource(snap());
    await mount(hud.source);
    await hud.push(snap({ camera_lost: true }));
    await hud.push(snap()); // the camera is back before any touch: nothing to tell
    await hud.push(snap({ unavailable: true, unavailable_reason: "no_face" }));
    await act(async () => chime.change?.(true));
    expect(sounds()).toEqual(["monitoring_unavailable"]);
    await hud.push(snap());
    expect(sounds()).toEqual(["monitoring_unavailable", "monitoring_restored"]);
  });
});

// Audit A4 H1 / M72: "does entering the demo still let a real alert be heard?"
describe("the scripted demo", () => {
  it("is never offered on #/live, nor on a device HUD that watches a driver", async () => {
    await mount(fakeSource(snap({ connected: false })).source);
    expect(shown().onToggleDemo).toBeUndefined();
    await act(async () => root.unmount());
    await mount(fakeSource(snap(), false).source);
    expect(shown().onToggleDemo).toBeUndefined();
  });

  it("sounds its scripted alerts, and does not listen to the source's pushes", async () => {
    const hud = fakeSource(snap({ connected: false }), false);
    await mount(hud.source);
    await act(async () => shown().onToggleDemo?.());
    expect(shown().demo).toBe(true);
    await wait(9000); // the script's first alert is 8 s in
    expect(chime.playAlert.mock.calls).toEqual([[1, ["drowsy_score"]]]);
  });

  it("a device that starts watching takes the screen back within one poll, and its alert is heard", async () => {
    const hud = fakeSource(null, false); // no device behind the screen yet
    await mount(hud.source);
    await wait(HUD_DEFAULTS.link_down_failures * POLL_MS);
    chime.play.mockClear();
    await act(async () => shown().onToggleDemo?.());
    await wait(2000);
    expect(shown().demo).toBe(true);
    expect(chime.playAlert).not.toHaveBeenCalled();

    hud.set(alerted("real-1", 3, "microsleep", { eyes_closed_s: 2 }));
    await wait(POLL_MS);
    expect(shown().demo).toBe(false);
    expect(shown().onToggleDemo).toBeUndefined(); // and the demo is no longer offered
    expect(chime.playAlert.mock.calls).toEqual([[3, ["microsleep"]]]);
    await wait(ALARM_MS);
    expect(sirens()).toBe(1);
  });
});
