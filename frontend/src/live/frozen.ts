// Does the camera hand over the same image again? (M83) A camera whose driver repeats its last frame
// still "delivers" frames: the loop then saw a face with open eyes that never moves, and said nothing.
// Every `stride`-th pixel (rows and columns) of a frame is compared with the previous frame's, as
// block 1 does on the device (edge_agent/capture/frame_source.py). A live sensor has noise, so two
// real frames are not equal. An image of one single value (covered or saturated lens: nothing in it
// can change) is never a repeat; block 6's quality check reports that one.
// Only the sparse pixels of one frame are kept, in memory.

export class RepeatCheck {
  private last: Uint8Array | null = null;

  /** stride 0 = off. */
  constructor(private stride: number) {}

  /** px: RGBA of the frame. True when its sparse pixels equal the previous frame's. */
  repeated(px: Uint8ClampedArray, width: number, height: number): boolean {
    const stride = this.stride;
    if (stride <= 0) return false;
    const n = Math.ceil(width / stride) * Math.ceil(height / stride) * 3;
    const last = this.last?.length === n ? this.last : null;
    const sample = last ?? new Uint8Array(n);
    let same = last != null;
    let flat = true;
    let at = 0;
    for (let y = 0; y < height; y += stride) {
      for (let x = 0; x < width; x += stride) {
        const i = (y * width + x) * 4;
        for (let c = 0; c < 3; c++, at++) {
          const v = px[i + c];
          if (sample[at] !== v) {
            same = false;
            sample[at] = v;
          }
          if (v !== px[0]) flat = false;
        }
      }
    }
    this.last = sample;
    return same && !flat;
  }
}
