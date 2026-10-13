// The canvas over the camera card of #/live that draws the driver's face (M104; geometry in
// faceDrawing.ts). Redrawn on the browser's animation frames from the agent's last frame, outside the
// processing loop: a few hundred short lines, well under a millisecond. Shown only, never kept.
import { useEffect, useRef } from "react";
import type { LiveAgent } from "./agent";
import { EYES, FACE_EDGES, NOSE_LINE, angleText, boxColor, coverView, faceBox, irisLine, toCanvas } from "./faceDrawing";

const STALE_MS = 500; // no new frame for this long: nothing drawn (the camera stalled)
const IRIS_GAIN = 4; // how much longer than the iris's offset its line is
const LINE = "#4ade80";
const IRIS = "#3b82f6";

export default function FaceOverlay({ agent }: { agent: LiveAgent }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    let id = 0;
    const draw = () => {
      id = requestAnimationFrame(draw);
      const canvas = ref.current;
      const ctx = canvas?.getContext("2d");
      if (!canvas || !ctx) return;
      const dpr = window.devicePixelRatio || 1;
      const bw = canvas.clientWidth;
      const bh = canvas.clientHeight;
      if (canvas.width !== Math.round(bw * dpr) || canvas.height !== Math.round(bh * dpr)) {
        canvas.width = Math.round(bw * dpr);
        canvas.height = Math.round(bh * dpr);
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, bw, bh);
      const face = agent.driverFace(STALE_MS);
      if (!face || bw === 0) return;
      const v = coverView(face.width, face.height, bw, bh);
      const at = (i: number) => toCanvas(v, face.points[i * 3], face.points[i * 3 + 1]);
      ctx.lineWidth = 1.5;
      ctx.lineJoin = "round";

      ctx.strokeStyle = LINE;
      ctx.beginPath();
      for (const e of FACE_EDGES) {
        const [x1, y1] = at(e.start);
        const [x2, y2] = at(e.end);
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
      }
      NOSE_LINE.forEach((i, k) => {
        const [x, y] = at(i);
        if (k) ctx.lineTo(x, y);
        else ctx.moveTo(x, y);
      });
      ctx.stroke();

      ctx.strokeStyle = IRIS;
      ctx.lineWidth = 2.5;
      ctx.beginPath();
      for (const eye of EYES) {
        const l = irisLine(face.points, eye, IRIS_GAIN);
        if (!l) continue;
        const [x1, y1] = toCanvas(v, l[0], l[1]);
        const [x2, y2] = toCanvas(v, l[2], l[3]);
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
      }
      ctx.stroke();

      const [fx1, fy1, fx2, fy2] = faceBox(face.points);
      if (!Number.isFinite(fx1)) return;
      const [ax, ay] = toCanvas(v, fx1, fy1);
      const [bx, by] = toCanvas(v, fx2, fy2);
      const color = boxColor(face.level);
      const left = Math.min(ax, bx);
      const top = Math.min(ay, by);
      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(left, top, Math.abs(bx - ax), Math.abs(by - ay));
      ctx.fillStyle = color;
      ctx.font = "400 13px ui-monospace, SFMono-Regular, Menlo, monospace"; // not bold (13/10)
      ctx.textBaseline = "bottom";
      const m = face.measures;
      ctx.fillText(angleText(m.yaw, m.pitch, m.roll), left, Math.max(14, top - 4));
    };
    id = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(id);
  }, [agent]);
  return <canvas ref={ref} aria-hidden data-testid="face-overlay" className="pointer-events-none absolute inset-0 size-full" />;
}
