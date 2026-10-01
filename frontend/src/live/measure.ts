// Raw measurements the in-browser agent takes on a frame (RGBA pixels from a canvas), ported from
// the device's Python so both see the same numbers. No thresholds here: the Python side
// (edge_agent/web/bridge.py) compares them with thresholds.yaml.

export type Box = [x1: number, y1: number, x2: number, y2: number];

/** BT.601 luma, the Y of OpenCV's BGR2YCrCb that block 2 uses as brightness. */
function luma(px: Uint8ClampedArray, i: number): number {
  return 0.299 * px[i] + 0.587 * px[i + 1] + 0.114 * px[i + 2];
}

/** Mean luminance 0-255 inside the box (block 5's face brightness), of the whole frame when the box is too small. */
export function meanLuma(px: Uint8ClampedArray, width: number, height: number, box: Box | null): number {
  let [x1, y1, x2, y2] = [0, 0, width, height];
  if (box) {
    const bx1 = Math.max(Math.floor(box[0]), 0);
    const by1 = Math.max(Math.floor(box[1]), 0);
    const bx2 = Math.min(Math.ceil(box[2]), width);
    const by2 = Math.min(Math.ceil(box[3]), height);
    if (bx2 - bx1 >= 2 && by2 - by1 >= 2) [x1, y1, x2, y2] = [bx1, by1, bx2, by2];
  }
  let sum = 0;
  for (let y = y1; y < y2; y++) {
    for (let x = x1; x < x2; x++) sum += luma(px, (y * width + x) * 4);
  }
  return sum / ((x2 - x1) * (y2 - y1));
}

/** Block 2's infrared test value: mean |B - G| and |G - R| on every 4th pixel (0 = grayscale / IR camera). */
export function channelDiff(px: Uint8ClampedArray, width: number, height: number): number {
  let bg = 0;
  let gr = 0;
  let n = 0;
  for (let y = 0; y < height; y += 4) {
    for (let x = 0; x < width; x += 4) {
      const i = (y * width + x) * 4;
      bg += Math.abs(px[i + 2] - px[i + 1]);
      gr += Math.abs(px[i + 1] - px[i]);
      n++;
    }
  }
  return n ? (bg / n + gr / n) / 2 : 0;
}

/** Same geometry as phone_detector.letterbox: resize keeping aspect, pad to size x size. */
export function letterboxGeometry(width: number, height: number, size: number) {
  const scale = Math.min(size / width, size / height);
  const w = Math.round(width * scale);
  const h = Math.round(height * scale);
  return { scale, w, h, padX: Math.floor((size - w) / 2), padY: Math.floor((size - h) / 2) };
}

/** Letterboxed RGBA (size x size) -> YOLO input: float32 NCHW, RGB, / 255 (cv2.dnn.blobFromImage). */
export function toChw(px: Uint8ClampedArray, size: number): Float32Array {
  const plane = size * size;
  const out = new Float32Array(3 * plane);
  for (let i = 0; i < plane; i++) {
    out[i] = px[i * 4] / 255;
    out[plane + i] = px[i * 4 + 1] / 255;
    out[2 * plane + i] = px[i * 4 + 2] / 255;
  }
  return out;
}

export interface Point3 {
  x: number;
  y: number;
  z: number;
}

/** Block 3: normalized MediaPipe landmarks -> pixels (z scaled like x), as FaceLandmarkDetector.detect. */
export function toPixels(face: readonly Point3[], width: number, height: number): Float32Array {
  const out = new Float32Array(face.length * 3);
  face.forEach((p, i) => {
    out[i * 3] = p.x * width;
    out[i * 3 + 1] = p.y * height;
    out[i * 3 + 2] = p.z * width;
  });
  return out;
}

export function bbox(points: Float32Array): Box {
  let [x1, y1, x2, y2] = [Infinity, Infinity, -Infinity, -Infinity];
  for (let i = 0; i < points.length; i += 3) {
    x1 = Math.min(x1, points[i]);
    x2 = Math.max(x2, points[i]);
    y1 = Math.min(y1, points[i + 1]);
    y2 = Math.max(y2, points[i + 1]);
  }
  return [x1, y1, x2, y2];
}

/** Faces (478 x 3 each) back to back, for one call into Python. */
export function concatFaces(faces: Float32Array[]): Float32Array {
  const out = new Float32Array(faces.reduce((n, f) => n + f.length, 0));
  let at = 0;
  for (const f of faces) {
    out.set(f, at);
    at += f.length;
  }
  return out;
}

/** The largest face (closest to the camera). Python picks the driver; this is for brightness. */
export function largestFace(faces: Float32Array[]): number {
  let best = -1;
  let area = -1;
  faces.forEach((f, i) => {
    const [x1, y1, x2, y2] = bbox(f);
    const a = (x2 - x1) * (y2 - y1);
    if (a > area) [best, area] = [i, a];
  });
  return best;
}
