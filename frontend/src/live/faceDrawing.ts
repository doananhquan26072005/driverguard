// The driver's face drawn over the camera card of #/live (M104), as a DMS shows it: a box round the
// face, the landmarks of the face's outline / brows / eyes / nose / lips joined by lines, the head's
// angles above the box and a short line from each iris. Drawn from the landmarks of the last frame
// (numbers), on the page only: no picture is made, kept or sent. Pure geometry here (tested); the
// canvas is FaceOverlay.tsx.
import { FaceLandmarker } from "@mediapipe/tasks-vision";

type Edge = { start: number; end: number };

/** Lines of the drawing: MediaPipe's own groups of the 478-point face mesh. */
export const FACE_EDGES: readonly Edge[] = [
  ...FaceLandmarker.FACE_LANDMARKS_FACE_OVAL,
  ...FaceLandmarker.FACE_LANDMARKS_LEFT_EYEBROW,
  ...FaceLandmarker.FACE_LANDMARKS_RIGHT_EYEBROW,
  ...FaceLandmarker.FACE_LANDMARKS_LEFT_EYE,
  ...FaceLandmarker.FACE_LANDMARKS_RIGHT_EYE,
  ...FaceLandmarker.FACE_LANDMARKS_LIPS,
];

/** Bridge and tip of the nose (MediaPipe has no group for it). */
export const NOSE_LINE: readonly number[] = [168, 6, 197, 195, 5, 4, 1];

/** Iris centre and the eye's two corners, per eye (the 478-point model's iris points are 468-477). */
export const EYES: readonly { iris: number; corners: [number, number] }[] = [
  { iris: 468, corners: [33, 133] },
  { iris: 473, corners: [362, 263] },
];

/** Colour of the box by alert level, as the HUD's: calm, L1 / L2, L3. */
export function boxColor(level: number): string {
  return level >= 3 ? "#ef4444" : level >= 1 ? "#fb923c" : "#facc15";
}

export interface View {
  scale: number; // canvas px per frame px
  dx: number;
  dy: number;
  width: number; // of the canvas
}

/** Where a frame of fw x fh lands in a box of bw x bh drawn with object-fit: cover (the <video>). */
export function coverView(fw: number, fh: number, bw: number, bh: number): View {
  const scale = Math.max(bw / fw, bh / fh);
  return { scale, dx: (bw - fw * scale) / 2, dy: (bh - fh * scale) / 2, width: bw };
}

/** A frame point on the canvas, mirrored as the <video> is (the driver sees a mirror). */
export function toCanvas(v: View, x: number, y: number): [number, number] {
  return [v.width - (x * v.scale + v.dx), y * v.scale + v.dy];
}

/** The landmarks' box in frame px: [x1, y1, x2, y2]. */
export function faceBox(points: Float32Array): [number, number, number, number] {
  let [x1, y1, x2, y2] = [Infinity, Infinity, -Infinity, -Infinity];
  for (let i = 0; i < points.length; i += 3) {
    const x = points[i];
    const y = points[i + 1];
    if (!Number.isFinite(x) || !Number.isFinite(y)) continue;
    x1 = Math.min(x1, x);
    y1 = Math.min(y1, y);
    x2 = Math.max(x2, x);
    y2 = Math.max(y2, y);
  }
  return [x1, y1, x2, y2];
}

/** "(yaw°, pitch°, roll°)" above the box; a dash for an angle not measured. */
export function angleText(yaw: number | null, pitch: number | null, roll: number | null): string {
  const a = (v: number | null) => (v == null ? "–" : `${Math.round(v)}°`);
  return `(${a(yaw)}, ${a(pitch)}, ${a(roll)})`;
}

/** The short line from an iris, in frame px: the iris's offset from the middle of its eye, made
 *  longer (a third of the eye at least, the eye's width at most). A rough direction of the eye only:
 *  the system measures no gaze. null without the point. */
export function irisLine(points: Float32Array, eye: (typeof EYES)[number], gain: number): [number, number, number, number] | null {
  const p = (i: number) => (i * 3 + 1 < points.length ? [points[i * 3], points[i * 3 + 1]] : null);
  const iris = p(eye.iris);
  const a = p(eye.corners[0]);
  const b = p(eye.corners[1]);
  if (!iris || !a || !b || ![...iris, ...a, ...b].every(Number.isFinite)) return null;
  const mid = [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
  const width = Math.hypot(b[0] - a[0], b[1] - a[1]);
  if (width <= 0) return null;
  const [ox, oy] = [iris[0] - mid[0], iris[1] - mid[1]];
  const off = Math.hypot(ox, oy);
  if (off < 1e-6) return null; // looking straight on: no direction to draw
  const len = Math.min(Math.max(off * gain, 0.3 * width), width); // long enough to be seen, never past the eye's width
  return [iris[0], iris[1], iris[0] + (ox / off) * len, iris[1] + (oy / off) * len];
}
