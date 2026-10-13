import { afterEach, describe, expect, it, vi } from "vitest";
import { steadyInterval } from "./ticker";

class FakeWorker {
  static last: FakeWorker;
  onmessage: (() => void) | null = null;
  onerror: (() => void) | null = null;
  posted: unknown[] = [];
  terminated = false;
  constructor() {
    FakeWorker.last = this;
  }
  postMessage(m: unknown) {
    this.posted.push(m);
  }
  terminate() {
    this.terminated = true;
  }
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("steadyInterval", () => {
  it("ticks come from a worker, which is told the period and ended by the returned function", () => {
    vi.stubGlobal("Worker", FakeWorker);
    const fn = vi.fn();
    const stop = steadyInterval(fn, 200);
    const w = FakeWorker.last;
    expect(w.posted).toEqual([200]);
    w.onmessage?.();
    w.onmessage?.();
    expect(fn).toHaveBeenCalledTimes(2);
    stop();
    expect(w.terminated).toBe(true);
  });

  it("a worker that fails hands over to a plain timer, which the returned function also ends", () => {
    vi.useFakeTimers();
    vi.stubGlobal("Worker", FakeWorker);
    const fn = vi.fn();
    const stop = steadyInterval(fn, 100);
    FakeWorker.last.onerror?.();
    expect(FakeWorker.last.terminated).toBe(true);
    vi.advanceTimersByTime(300);
    expect(fn).toHaveBeenCalledTimes(3);
    stop();
    vi.advanceTimersByTime(300);
    expect(fn).toHaveBeenCalledTimes(3);
  });

  it("without workers a plain timer stands in", () => {
    vi.useFakeTimers();
    vi.stubGlobal("Worker", undefined);
    const fn = vi.fn();
    const stop = steadyInterval(fn, 50);
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(2);
    stop();
    vi.advanceTimersByTime(100);
    expect(fn).toHaveBeenCalledTimes(2);
  });
});
