// Tiny chart math: linear scales and clean ticks (no chart library).

export interface LinearScale {
  (value: number): number;
  domain: [number, number];
  range: [number, number];
  invert(px: number): number;
}

export function linearScale(domain: [number, number], range: [number, number]): LinearScale {
  const [d0, d1] = domain;
  const [r0, r1] = range;
  const span = d1 - d0 || 1;
  const scale = ((v: number) => r0 + ((v - d0) / span) * (r1 - r0)) as LinearScale;
  scale.domain = domain;
  scale.range = range;
  scale.invert = (px: number) => d0 + ((px - r0) / (r1 - r0 || 1)) * span;
  return scale;
}

/** Round tick values ("nice" steps of 1, 2, 5 x 10^n) covering [min, max]. */
export function niceTicks(min: number, max: number, count = 5): number[] {
  if (!(max > min)) return [min];
  const raw = (max - min) / Math.max(1, count);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 5, 10].map((m) => m * mag).find((s) => s >= raw) ?? 10 * mag;
  const ticks: number[] = [];
  for (let v = Math.ceil(min / step) * step; v <= max + step * 1e-9; v += step) {
    ticks.push(Number(v.toFixed(10)));
  }
  return ticks;
}

const MINUTE = 60_000;
const TIME_STEPS = [1, 2, 5, 10, 15, 30, 60, 120, 180, 360, 720, 1440].map((m) => m * MINUTE);

/** Time ticks (ms epoch) on round minute / hour boundaries, about `count` of them. */
export function timeTicks(start: number, end: number, count = 6): number[] {
  if (!(end > start)) return [start];
  const step = TIME_STEPS.find((s) => (end - start) / s <= count) ?? TIME_STEPS[TIME_STEPS.length - 1];
  const offset = new Date(start).getTimezoneOffset() * MINUTE; // align to local clock boundaries
  const ticks: number[] = [];
  for (let t = Math.ceil((start - offset) / step) * step + offset; t <= end; t += step) ticks.push(t);
  return ticks;
}

/** Index of the item whose x is closest to `x` (items sorted by x). -1 when empty. */
export function nearestIndex(xs: number[], x: number): number {
  if (xs.length === 0) return -1;
  let lo = 0;
  let hi = xs.length - 1;
  while (hi - lo > 1) {
    const mid = (lo + hi) >> 1;
    if (xs[mid] < x) lo = mid;
    else hi = mid;
  }
  return Math.abs(xs[lo] - x) <= Math.abs(xs[hi] - x) ? lo : hi;
}
