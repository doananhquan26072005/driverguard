// Is the loop still getting camera frames? (M71) #/live only runs when the browser calls
// requestVideoFrameCallback. When that went quiet the page stood still until someone reloaded it, and
// a camera that ended was never opened again. The loop asks this on a timer:
//   - no frame for capture.frame_timeout_s while the camera is live: pull frames with a timer;
//   - pulling brings none either, the track is muted that long, or it ended: the camera is lost, and
//     is asked for again every capture.reconnect_interval_s (as block 1 does on the device).
// Pure logic on the times it is given: tested without a browser.

export type CameraTrack = "live" | "muted" | "ended";

export interface WatchVerdict {
  pull: boolean; // drive the loop from a timer until the browser's own frame callback is heard again
  lost: boolean; // the camera gives no frames: the driver is not monitored
  reopen: number; // > 0: ask for the camera again now, this is attempt number `reopen`
}

export class LoopWatchdog {
  private lastFrameMs: number;
  private pullSince: number | null = null;
  private lost = false;
  private attempts = 0;
  private nextReopenMs = -Infinity;

  /** reconnectMs 0 = a lost camera is never asked for again. */
  constructor(
    private timeoutMs: number,
    private reconnectMs: number,
    startMs: number,
  ) {
    this.lastFrameMs = startMs;
  }

  /** A camera frame not seen before reached the loop. pulled: by the timer, not the browser's callback. */
  frame(nowMs: number, pulled: boolean) {
    this.lastFrameMs = nowMs;
    if (!pulled) this.pullSince = null;
    this.lost = false;
    this.attempts = 0;
  }

  /** The camera was opened again: it gets the frame timeout to deliver before the next attempt. */
  reopened(nowMs: number) {
    this.nextReopenMs = nowMs + Math.max(this.timeoutMs, this.reconnectMs);
  }

  /** visible false (tab in the background): the browser holds the frame callback back on purpose and
   *  slows timers to about one a second, too few frames to time anything on. Nothing is pulled then;
   *  the heartbeat says "stalled" as before. */
  check(nowMs: number, track: CameraTrack, visible: boolean): WatchVerdict {
    const quiet = nowMs - this.lastFrameMs >= this.timeoutMs;
    if (track === "ended" || (quiet && track === "muted")) this.lost = true;
    else if (quiet && !this.lost && visible) {
      if (this.pullSince == null) this.pullSince = nowMs;
      else if (nowMs - this.pullSince >= this.timeoutMs) this.lost = true; // the video itself stands still
    }
    let reopen = 0;
    if (this.lost && this.reconnectMs > 0 && nowMs >= this.nextReopenMs) {
      this.nextReopenMs = nowMs + this.reconnectMs;
      reopen = ++this.attempts;
    }
    return { pull: this.pullSince != null && track !== "ended", lost: this.lost, reopen };
  }
}
