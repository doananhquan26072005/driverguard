import { describe, expect, it } from "vitest";
import { FORCED_LOG_MAX, appendForced, forcedEntry, forcedLogFile } from "./forcedLog";

describe("forced-state log of the HUD preview (PRD FR-17)", () => {
  it("tags every hand-picked state simulated and forced", () => {
    const e = forcedEntry("l3", "L3 ngủ gật", "l0", true, new Date("2026-10-05T08:00:00Z"));
    expect(e).toEqual({
      at: "2026-10-05T08:00:00.000Z",
      state: "l3",
      label: "L3 ngủ gật",
      from: "l0",
      night: true,
      tags: ["simulated", "forced"],
    });
  });

  it("keeps the order and drops the oldest beyond the limit", () => {
    let log = appendForced([], forcedEntry("l1", "L1", null, false));
    log = appendForced(log, forcedEntry("l2o", "L2", "l1", false));
    expect(log.map((e) => e.state)).toEqual(["l1", "l2o"]);
    for (let i = 0; i < FORCED_LOG_MAX; i++) log = appendForced(log, forcedEntry(`s${i}`, "x", null, false));
    expect(log).toHaveLength(FORCED_LOG_MAX);
    expect(log[0].state).toBe("s0");
  });

  it("writes a file that says the entries are not measurements", () => {
    const file = JSON.parse(forcedLogFile([forcedEntry("off", "Tạm ngưng", "l0", false)]));
    expect(file.note).toContain("never used for any metric");
    expect(file.entries[0].tags).toEqual(["simulated", "forced"]);
  });
});
