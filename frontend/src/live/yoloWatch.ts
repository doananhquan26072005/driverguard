// Is the phone detector's worker still answering? (A1 M1 of the 08/10 audit) A run is handed to the
// worker and the loop waits for its answer before it hands over the next one. A worker that never
// answered (a hung session, a lost GPU device, a thread pool that deadlocked) left the detector
// "busy" for the rest of the trip: no error, no result, phone detection off until the page was reloaded.
//   - no answer for phone.web_run_timeout_s: the worker is terminated and a new one is built;
//   - at most phone.web_restart_limit replacements in a row without a result between them: a machine
//     where every worker hangs must not rebuild a session every few seconds for the whole trip. Then
//     the detector stays off, and Python reports that as it reports one that never loaded (M50).
// Pure logic on the times it is given: tested without a browser.

export type YoloVerdict = "ok" | "restart" | "give_up";

export class YoloWatch {
  private sentMs: number | null = null; // when the run still waited for was handed over
  private inRow = 0; // replacements since the last result

  /** timeoutMs 0 or less = a silent worker is never replaced (as before). */
  constructor(
    private timeoutMs: number,
    private limit: number,
  ) {}

  /** A run was handed to the worker. */
  sent(nowMs: number) {
    this.sentMs = nowMs;
  }

  /** The worker answered the run. result false: with an error, which proves it alive but not working. */
  answered(result: boolean) {
    this.sentMs = null;
    if (result) this.inRow = 0;
  }

  /** Called on a timer. "restart": replace the worker now; "give_up": drop it, the limit is reached. */
  check(nowMs: number): YoloVerdict {
    if (this.sentMs == null || this.timeoutMs <= 0 || nowMs - this.sentMs < this.timeoutMs) return "ok";
    this.sentMs = null; // this run is given up; the verdict is returned once
    if (this.inRow >= this.limit) return "give_up";
    this.inRow += 1;
    return "restart";
  }
}
