// When the phone detector gets a frame (M67). The loop offers every frame; the detector takes one
// about `targetFps` times a second and never while it is still busy with the previous one.
//
// Before, a frame was taken once "at least 1 / targetFps since the last one" had passed. Camera frames
// come 33 ms apart with a little jitter, so the frame 200 ms later was "not yet" about half the time
// and the next one (233 ms) was taken instead: 4.5 runs a second for a target of 5. Every result was
// then in use that much longer, and its age on a frame is what phone.max_result_age_s judges.

export class YoloPacer {
  private due = -Infinity; // frame time (s) the next run is due at
  private lastT: number | null = null;

  /** targetFps: phone.target_fps on wasm, phone.web_gpu_target_fps on WebGPU; 0 or less = the detector never runs. */
  constructor(private targetFps: number) {}

  /** One camera frame taken at `t` seconds; busy: the detector has not answered its last frame yet.
   *  True = hand this frame to the detector. */
  take(t: number, busy: boolean): boolean {
    const dt = this.lastT == null ? 0 : Math.max(t - this.lastT, 0); // time between frames, as it is now
    this.lastT = t;
    if (busy || this.targetFps <= 0) return false;
    // The frame nearest the due time, not the first one past it.
    if (t + dt / 2 < this.due) return false;
    const period = 1 / this.targetFps;
    // On time (within a frame of the due time): keep the rhythm, so the rate is the target on average.
    // Late (the detector was busy, the loop stalled, the first frame): start again from this frame,
    // so runs never come in a burst to catch up.
    this.due = t - this.due < Math.max(dt, 1e-3) ? this.due + period : t + period;
    return true;
  }
}
