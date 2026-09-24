// Fatigue timeline: one line (drowsy_score per minute, 0-100) with the L1 / L2 thresholds and
// the alerts of the trip as markers. Hand-written SVG; hover shows a crosshair + tooltip.
import { type PointerEvent, useEffect, useMemo, useRef, useState } from "react";
import { formatNumber, formatPercent, formatTime } from "../lib/format";
import { LEVELS, reasonText } from "../lib/labels";
import { linearScale, nearestIndex, niceTicks, timeTicks } from "../lib/scale";
import type { EventRecord, SampleRecord } from "../lib/types";

const HEIGHT = 280;
const M = { top: 16, right: 64, bottom: 28, left: 40 };
const EVENT_HIT_PX = 10;

interface Props {
  samples: SampleRecord[];
  events: EventRecord[];
  l1: number;
  l2: number;
}

export default function FatigueChart({ samples, events, l1, l2 }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(720);
  const [hoverX, setHoverX] = useState<number | null>(null);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(320, entry.contentRect.width)));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const points = useMemo(() => samples.map((s) => ({ t: Date.parse(s.ts), s })), [samples]);
  const marks = useMemo(() => events.map((e) => ({ t: Date.parse(e.ts), e })), [events]);

  const allT = [...points.map((p) => p.t), ...marks.map((m) => m.t)];
  let t0 = Math.min(...allT);
  let t1 = Math.max(...allT);
  if (!(t1 > t0)) {
    t0 -= 60_000;
    t1 += 60_000;
  }
  const x = linearScale([t0, t1], [M.left, width - M.right]);
  const y = linearScale([0, 100], [HEIGHT - M.bottom, M.top]);
  const yTicks = niceTicks(0, 100, 5);
  const xTicks = timeTicks(t0, t1, Math.max(2, Math.floor((width - M.left - M.right) / 110)));

  const line = points.map((p, i) => `${i ? "L" : "M"}${x(p.t).toFixed(1)},${y(p.s.drowsy_score).toFixed(1)}`).join("");
  const area =
    points.length > 1
      ? `${line}L${x(points[points.length - 1].t).toFixed(1)},${y(0)}L${x(points[0].t).toFixed(1)},${y(0)}Z`
      : "";

  // Hover: nearest minute sample, or an alert marker under the pointer.
  const hoverIdx = hoverX == null ? -1 : nearestIndex(points.map((p) => x(p.t)), hoverX);
  const hoverEvent =
    hoverX == null ? undefined : marks.find((m) => Math.abs(x(m.t) - hoverX) <= EVENT_HIT_PX);
  const hoverPoint = hoverIdx >= 0 ? points[hoverIdx] : undefined;
  const crossX = hoverEvent ? x(hoverEvent.t) : hoverPoint ? x(hoverPoint.t) : null;

  function onMove(ev: PointerEvent<SVGSVGElement>) {
    const box = ev.currentTarget.getBoundingClientRect();
    setHoverX(((ev.clientX - box.left) / box.width) * width);
  }

  return (
    <div className="chart" ref={wrapRef}>
      <svg
        width={width}
        height={HEIGHT}
        viewBox={`0 0 ${width} ${HEIGHT}`}
        role="img"
        aria-label="drowsy_score theo từng phút của chuyến đi, kèm các cảnh báo"
        onPointerMove={onMove}
        onPointerLeave={() => setHoverX(null)}
      >
        {yTicks.map((v) => (
          <g key={v}>
            <line className="grid" x1={M.left} x2={width - M.right} y1={y(v)} y2={y(v)} />
            <text className="axis-label" x={M.left - 8} y={y(v)} dy="0.32em" textAnchor="end">
              {v}
            </text>
          </g>
        ))}
        {xTicks.map((t) => (
          <text key={t} className="axis-label" x={x(t)} y={HEIGHT - 8} textAnchor="middle">
            {formatTime(t).slice(0, 5)}
          </text>
        ))}
        <line className="baseline" x1={M.left} x2={width - M.right} y1={y(0)} y2={y(0)} />

        {[
          { v: l1, label: `L1 · ${l1}` },
          { v: l2, label: `L2 · ${l2}` },
        ].map((ref) => (
          <g key={ref.label}>
            <line className="ref-line" x1={M.left} x2={width - M.right} y1={y(ref.v)} y2={y(ref.v)} />
            <text className="ref-label" x={width - M.right + 6} y={y(ref.v)} dy="0.32em">
              {ref.label}
            </text>
          </g>
        ))}

        {area && <path className="series-area" d={area} />}
        {points.length > 0 && <path className="series-line" d={line} />}
        {points.length === 1 && <circle className="series-dot" cx={x(points[0].t)} cy={y(points[0].s.drowsy_score)} r={4} />}

        {crossX != null && <line className="crosshair" x1={crossX} x2={crossX} y1={M.top} y2={HEIGHT - M.bottom} />}
        {hoverPoint && !hoverEvent && (
          <circle className="series-dot" cx={x(hoverPoint.t)} cy={y(hoverPoint.s.drowsy_score)} r={4} />
        )}

        {marks.map(({ t, e }) => (
          <circle
            key={e.event_id}
            className={`alert-mark level-${e.level}${e.feedback ? " false-alarm" : ""}`}
            cx={x(t)}
            cy={y(Math.min(e.drowsy_score, 100))}
            r={hoverEvent?.e.event_id === e.event_id ? 7 : 5}
          />
        ))}
      </svg>

      {crossX != null && (hoverEvent || hoverPoint) && (
        <div
          className="tooltip"
          style={{
            left: Math.min(crossX + 12, width - 220),
            top: M.top,
          }}
        >
          {hoverEvent ? (
            <>
              <div className="tooltip-title">
                {LEVELS[hoverEvent.e.level].icon} Cảnh báo {LEVELS[hoverEvent.e.level].short} · {formatTime(hoverEvent.t)}
              </div>
              <div>{hoverEvent.e.reasons.map(reasonText).join(", ")}</div>
              <div className="muted">
                Buồn ngủ {formatNumber(hoverEvent.e.drowsy_score)} · Mất tập trung{" "}
                {formatNumber(hoverEvent.e.distraction_score)}
              </div>
              {hoverEvent.e.feedback && <div className="tag">Tài xế báo sai</div>}
            </>
          ) : (
            hoverPoint && (
              <>
                <div className="tooltip-title">Phút kết thúc {formatTime(hoverPoint.t)}</div>
                <div>
                  drowsy_score <strong>{formatNumber(hoverPoint.s.drowsy_score, 1)}</strong>
                </div>
                <div className="muted">
                  PERCLOS {formatPercent(hoverPoint.s.perclos_60s, 1)} · mức cao nhất {LEVELS[hoverPoint.s.max_level].short}
                </div>
              </>
            )
          )}
        </div>
      )}

      <ul className="legend" aria-label="Chú thích">
        <li>
          <span className="key-line" aria-hidden /> drowsy_score trung bình mỗi phút
        </li>
        {([1, 2, 3] as const).map((lv) => (
          <li key={lv}>
            <span className={`key-dot level-${lv}`} aria-hidden /> {LEVELS[lv].icon} Cảnh báo {LEVELS[lv].short}
          </li>
        ))}
        <li>
          <span className="key-dot hollow" aria-hidden /> Tài xế báo sai
        </li>
      </ul>
    </div>
  );
}
