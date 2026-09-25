import { describe, expect, it } from "vitest";
import type { HudSnapshot } from "../lib/types";
import { orderedReasons, primaryReason, systemState } from "./hudModel";

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
});
