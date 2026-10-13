// Pieces of a trip shared by the driver's pages (M61) and the manager's report review (M62), on the
// design system: the assessment card in the trip's colour, the whole-trip fatigue bars with a time axis,
// a stat tile. Plain words for drivers; the engineer numbers stay in TripReports.
import { CircleAlert, CircleCheck, OctagonAlert, type LucideIcon } from "lucide-react";
import { formatDateTime } from "../lib/format";
import type { TripRating, TripReport, TripSummary } from "../lib/types";
import { RATING_TEXT, driverStory, summaryBars, type Zone } from "../hud/tripModel";

const RATING_TONE: Record<TripRating, { card: string; dot: string; icon: string; Icon: LucideIcon }> = {
  good: { card: "l0", dot: "var(--good)", icon: "var(--good)", Icon: CircleCheck },
  attention: { card: "l1", dot: "var(--warning)", icon: "var(--warning)", Icon: CircleAlert },
  risk: { card: "l3t", dot: "#f87171", icon: "#f87171", Icon: OctagonAlert },
};
const ZONE_COLOR: Record<Zone, string> = { awake: "#4ade80", tired: "#fbbf24", very_tired: "#f87171" };

export const dayText = (iso: string) => {
  const d = new Date(iso);
  const weekday = new Intl.DateTimeFormat("vi-VN", { weekday: "long" }).format(d);
  return `${weekday.charAt(0).toUpperCase()}${weekday.slice(1)} ${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
};
export const hm = (iso: string) => {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
};
export const span = (s: TripSummary) => `${hm(s.started_at)} – ${hm(s.ended_at)}`;

export function RatingChip({ rating }: { rating: TripRating }) {
  return (
    <span className="dg-chip" style={{ ["--dot" as string]: RATING_TONE[rating].dot }}>
      <i />
      {RATING_TEXT[rating].title}
    </span>
  );
}

/** "quanly đã xem lúc 10:42" / "Chưa có ai xem": the driver knows the report reached a manager. */
/** The reviewer's note for the driver (M105), or null when there is none. */
export function reviewNote(r: TripReport): string | null {
  return r.review_note?.trim() || null;
}

export function reviewedText(r: TripReport): string {
  return r.reviewed_at ? `${r.reviewed_by ?? "Quản lý"} đã xem lúc ${formatDateTime(r.reviewed_at)}` : "Quản lý chưa xem";
}

export function RatingCard({ report, title, children }: { report: TripReport; title: string; children?: React.ReactNode }) {
  const s = report.summary;
  const tone = RATING_TONE[report.rating];
  const text = RATING_TEXT[report.rating];
  return (
    <section className={`dg-alert ${tone.card} trip-rating`}>
      <div className="row-between">
        <span className="dg-card-title">
          <b>{title}</b>
          <span>
            {dayText(s.started_at)} · {span(s)} · xe {report.device_id}
          </span>
        </span>
        <RatingChip rating={report.rating} />
      </div>
      <div className="trip-rating-head">
        <span className="dg-tile trip-rating-icon" style={{ color: tone.icon }}>
          <tone.Icon aria-hidden size={34} strokeWidth={1.75} />
        </span>
        <div>
          <h2>{text.title}</h2>
          <p className="muted">{text.detail}</p>
        </div>
      </div>
      <p className="trip-story">{driverStory(s)}</p>
      {children}
    </section>
  );
}

export function TripBars({ summary: s, height = 140 }: { summary: TripSummary; height?: number }) {
  const { perBar, bars } = summaryBars(s);
  const start = Date.parse(s.started_at);
  const end = Date.parse(s.ended_at);
  const at = (ms: number) => hm(new Date(ms).toISOString());
  return (
    <div className="trip-bars">
      <div
        role="img"
        aria-label={`Độ mệt theo thời gian của ca lái${s.first_tired_min != null ? `: có dấu hiệu mệt từ phút lái thứ ${s.first_tired_min}` : ""}`}
        className="trip-bars-plot"
        style={{ height }}
      >
        {bars.map((b, i) => (
          <div
            key={i}
            style={{
              height: `${b.stopped ? 4 : Math.max(4, Math.min(100, b.score))}%`,
              background: b.stopped ? "rgba(255,255,255,0.12)" : ZONE_COLOR[b.zone],
            }}
          />
        ))}
      </div>
      <div className="trip-bars-axis dg-num">
        <span>{at(start)}</span>
        <span>{perBar} phút mỗi cột</span>
        <span>{at(end)}</span>
      </div>
      <div className="trip-legend">
        {(
          [
            ["#4ade80", "Tỉnh táo"],
            ["#fbbf24", "Hơi mệt"],
            ["#f87171", "Rất mệt"],
            ["rgba(255,255,255,0.25)", "Xe dừng"],
          ] as const
        ).map(([c, t]) => (
          <span key={t}>
            <i style={{ background: c }} />
            {t}
          </span>
        ))}
      </div>
    </div>
  );
}

export function Tile({ icon: Icon, value, label, accent }: { icon: LucideIcon; value: string; label: string; accent?: string }) {
  return (
    <div className="dg-tile web-tile">
      <span className="dg-tile web-tile-icon" style={accent ? { color: accent } : undefined}>
        <Icon aria-hidden size={18} />
      </span>
      <span>
        <b className="dg-num">{value}</b>
        <span className="muted">{label}</span>
      </span>
    </div>
  );
}
