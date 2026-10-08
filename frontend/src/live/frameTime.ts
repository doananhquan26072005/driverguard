// When was this frame taken? (M50) The loop used to stamp a frame with the time it got round to
// processing it, so every duration the decision chain measures (eyes closed, a blink, looking away)
// carried the jitter of the processing time. requestVideoFrameCallback says when the camera captured
// the frame, on the same clock as performance.now().

/** The part of VideoFrameCallbackMetadata the loop reads. */
export interface FrameMetadata {
  captureTime?: number; // camera / WebRTC sources: when the frame was captured
  presentationTime?: number; // when the browser handed the frame to the compositor
  presentedFrames?: number;
}

/** Time of the frame in ms on the performance.now() clock: its capture time when the browser gives a
 *  believable one (not in the future, not older than maxAgeMs, after the previous frame's), else its
 *  presentation time under the same checks, else `nowMs` as before. maxAgeMs: a capture time further
 *  back is not believed (a stalled tab, another clock); thresholds.yaml capture.web_max_frame_age_s. */
export function frameTimeMs(nowMs: number, meta: FrameMetadata | undefined, lastMs: number, maxAgeMs: number): number {
  for (const candidate of [meta?.captureTime, meta?.presentationTime]) {
    if (candidate == null || !Number.isFinite(candidate)) continue;
    if (candidate <= nowMs && nowMs - candidate <= maxAgeMs && candidate > lastMs) return candidate;
  }
  return nowMs;
}
