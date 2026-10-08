import { describe, expect, it } from "vitest";
import { YoloWatch } from "./yoloWatch";

const TIMEOUT = 5000; // phone.web_run_timeout_s
const LIMIT = 3; // phone.web_restart_limit

describe("YoloWatch", () => {
  it("says nothing while runs are answered, however slowly below the timeout", () => {
    const w = new YoloWatch(TIMEOUT, LIMIT);
    for (let t = 0; t < 600_000; t += 1200) {
      w.sent(t);
      expect(w.check(t + 1199)).toBe("ok"); // 1.2 s a run: the estimate for the target box
      w.answered(true);
    }
    expect(w.check(700_000)).toBe("ok"); // idle: nothing is waited for
  });

  it("replaces a worker that has not answered for the timeout, once", () => {
    const w = new YoloWatch(TIMEOUT, LIMIT);
    w.sent(1000);
    expect(w.check(5999)).toBe("ok");
    expect(w.check(6000)).toBe("restart");
    expect(w.check(7000)).toBe("ok"); // the new worker is being built: no run is out
    expect(w.check(60_000)).toBe("ok");
  });

  it("gives up after the limit of replacements in a row", () => {
    const w = new YoloWatch(TIMEOUT, LIMIT);
    const verdicts = [];
    for (let i = 0; i < 5; i++) {
      w.sent(i * 10_000);
      verdicts.push(w.check(i * 10_000 + TIMEOUT));
    }
    expect(verdicts).toEqual(["restart", "restart", "restart", "give_up", "give_up"]);
  });

  it("starts counting again after a result", () => {
    const w = new YoloWatch(TIMEOUT, LIMIT);
    let t = 0;
    for (let round = 0; round < 4; round++) {
      // three hangs, then the fourth worker answers: never more than the limit in a row
      for (let i = 0; i < LIMIT; i++) {
        w.sent(t);
        expect(w.check((t += TIMEOUT))).toBe("restart");
      }
      w.sent(t);
      w.answered(true);
      t += 200;
    }
  });

  it("does not take an error answer for a working detector", () => {
    const w = new YoloWatch(TIMEOUT, 1);
    w.sent(0);
    expect(w.check(TIMEOUT)).toBe("restart");
    w.sent(6000);
    w.answered(false); // alive, but no result
    expect(w.check(60_000)).toBe("ok"); // and nothing is waited for
    w.sent(61_000);
    expect(w.check(66_000)).toBe("give_up");
  });

  it("is off with a timeout of 0", () => {
    const w = new YoloWatch(0, LIMIT);
    w.sent(0);
    expect(w.check(3_600_000)).toBe("ok");
  });

  it("with a limit of 0 only drops the silent worker", () => {
    const w = new YoloWatch(TIMEOUT, 0);
    w.sent(0);
    expect(w.check(TIMEOUT)).toBe("give_up");
  });
});
