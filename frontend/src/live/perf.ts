// Where the in-browser loop spends its time (M49): one sample per frame and stage, kept for the last
// few seconds, summarised as p50 / p95 / max. Shown under "Chi tiết kỹ thuật" of #/live and sent with
// the heartbeat (numbers only), so a slow hub says which stage is slow. The Python side
// (edge_agent/io/publisher.py perf_record) and the backend (schemas.PerfIn) accept exactly these names.

import type { PerfSnapshot, PerfStage, StageMs } from "../lib/types";

export type { PerfSnapshot, StageMs };
export type Stage = PerfStage;

/** camera_lag: from the camera capturing a frame to the loop starting on it (M50);
 *  capture: video -> canvas -> pixels; landmarks: MediaPipe; measure: brightness / sharpness in JS;
 *  yolo_prep: letterbox + tensor for the worker (only on frames that feed YOLO); python: blocks 6-14 in
 *  Pyodide + JSON; frame: all of it; yolo: one inference in the worker; yolo_age: how old the YOLO
 *  result in use is on a frame (phone.max_result_age_s decides when it stops counting). */
export const STAGES: readonly Stage[] = ["camera_lag", "capture", "landmarks", "measure", "yolo_prep", "python", "total", "yolo", "yolo_age"];

const round1 = (v: number) => Math.round(v * 10) / 10;

/** p50 / p95 / max of the samples (ms, one decimal), null without any. */
export function summarize(samples: ArrayLike<number>): StageMs | null {
  const n = samples.length;
  if (!n) return null;
  const sorted = Float64Array.from(samples).sort();
  const at = (p: number) => sorted[Math.min(n - 1, Math.floor(p * n))];
  return { p50: round1(at(0.5)), p95: round1(at(0.95)), max: round1(sorted[n - 1]) };
}

/** The last `size` values, without allocating per sample. */
class Ring {
  private buf: Float64Array;
  private next = 0;
  private count = 0;
  constructor(size: number) {
    this.buf = new Float64Array(size);
  }
  push(v: number) {
    this.buf[this.next] = v;
    this.next = (this.next + 1) % this.buf.length;
    this.count = Math.min(this.count + 1, this.buf.length);
  }
  values(): Float64Array {
    return this.buf.subarray(0, this.count); // order does not matter to a summary
  }
}

export class PerfWindow {
  private rings = new Map<Stage, Ring>();
  private presented: Ring;
  private knowsPresented = false;

  /** size: samples kept per stage (300 = 10 s of frames at 30 FPS, a minute of YOLO runs at 5 / s). */
  constructor(private size = 300) {
    this.presented = new Ring(size);
  }

  add(stage: Stage, ms: number) {
    if (!Number.isFinite(ms) || ms < 0) return;
    let ring = this.rings.get(stage);
    if (!ring) this.rings.set(stage, (ring = new Ring(this.size)));
    ring.push(ms);
  }

  /** Once per processed frame: how many frames the camera delivered since the previous one
   *  (requestVideoFrameCallback's presentedFrames difference; 1 = none was skipped). */
  cameraFrames(sinceLast: number) {
    if (!Number.isFinite(sinceLast) || sinceLast < 1) return;
    this.knowsPresented = true;
    this.presented.push(sinceLast);
  }

  snapshot(landmarksDelegate: PerfSnapshot["landmarks_delegate"], yoloThreads: number | null): PerfSnapshot {
    const stages_ms: PerfSnapshot["stages_ms"] = {};
    for (const stage of STAGES) {
      const s = summarize(this.rings.get(stage)?.values() ?? []);
      if (s) stages_ms[stage] = s;
    }
    const deltas = this.presented.values();
    const camera = deltas.reduce((a, b) => a + b, 0);
    return {
      samples: this.rings.get("total")?.values().length ?? 0,
      stages_ms,
      landmarks_delegate: landmarksDelegate,
      yolo_threads: yoloThreads,
      camera_delivered: this.knowsPresented ? camera : null,
      camera_dropped: this.knowsPresented ? camera - deltas.length : null,
    };
  }
}
