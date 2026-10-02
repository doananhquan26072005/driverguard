// End-of-trip screen for the driver (after "Kết thúc chuyến"): the assessment, a plain-language
// story, a few big facts, the fatigue of every minute in three colour zones, suggestions, and
// where the summary went. No variable names, no L0-L3: the engineer version is on the dashboard.
import { CircleAlert, OctagonAlert, Send, ShieldCheck, type LucideIcon } from "lucide-react";
import type { TripDelivery, TripRating, TripSummary } from "../lib/types";
import {
  DELIVERY_TEXT,
  RATING_REASON_TEXT,
  RATING_TEXT,
  ZONE_TEXT,
  driverStory,
  formatDuration,
  suggestionText,
  zoneOf,
  type Zone,
} from "./tripModel";

const RATING_TONE: Record<TripRating, { ring: string; icon: string; Icon: LucideIcon }> = {
  good: { ring: "ring-hud-safe", icon: "text-hud-safe", Icon: ShieldCheck },
  attention: { ring: "ring-hud-caution", icon: "text-hud-caution", Icon: CircleAlert },
  risk: { ring: "ring-hud-danger", icon: "text-hud-danger", Icon: OctagonAlert },
};

const ZONE_FILL: Record<Zone, string> = {
  awake: "fill-hud-safe",
  tired: "fill-hud-caution",
  very_tired: "fill-hud-danger",
};
const ZONE_DOT: Record<Zone, string> = { awake: "bg-hud-safe", tired: "bg-hud-caution", very_tired: "bg-hud-danger" };

interface Props {
  summary: TripSummary;
  delivery: TripDelivery;
  onDone: () => void;
}

export default function TripSummaryView({ summary: s, delivery, onDone }: Props) {
  const tone = RATING_TONE[s.rating];
  const rating = RATING_TEXT[s.rating];
  const reminders = Object.values(s.alerts_by_reason).reduce((a, b) => a + (b ?? 0), 0);
  const reasons = s.rating_reasons.filter((r) => r !== "low_coverage" || s.rating === "good");

  return (
    <div className="min-h-dvh bg-hud-bg font-hud text-hud-ink antialiased [color-scheme:dark]">
      <main className="mx-auto grid max-w-3xl gap-6 px-4 py-8 sm:py-12">
        <p className="m-0 text-hud-label font-bold tracking-tight text-hud-system">DriverGuard · Tổng kết chuyến đi</p>

        <section aria-live="polite" className={`flex flex-col gap-4 rounded-hud-lg bg-hud-surface p-6 ring-2 sm:p-8 ${tone.ring}`}>
          <div className="flex items-center gap-4">
            <tone.Icon aria-hidden strokeWidth={1.75} className={`size-14 shrink-0 sm:size-16 ${tone.icon}`} />
            <div className="min-w-0">
              <h1 className="m-0 text-hud-title font-extrabold text-balance">{rating.title}</h1>
              <p className="m-0 mt-1 text-hud-body text-hud-ink-2">{rating.detail}</p>
            </div>
          </div>
          <p className="m-0 text-hud-body text-pretty">{driverStory(s)}</p>
          {reasons.length > 0 && (
            <ul className="m-0 grid gap-1 pl-5 text-hud-label text-hud-ink-2">
              {reasons.map((r) => (
                <li key={r}>{RATING_REASON_TEXT[r]}</li>
              ))}
            </ul>
          )}
        </section>

        <section aria-label="Số liệu chính" className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Fact label="Thời gian lái" value={formatDuration(s.driving_s)} />
          <Fact label="Lần nghỉ" value={String(s.rests)} />
          <Fact label="Lần nhắc nhở" value={String(reminders)} />
          <Fact label="Báo sai bạn đã bấm" value={String(s.false_alarms)} />
        </section>

        <MinuteChart summary={s} />

        {s.suggestions.length > 0 && (
          <section className="grid gap-3 rounded-hud bg-hud-surface p-6 ring-1 ring-hud-line">
            <h2 className="m-0 text-hud-body font-semibold">Gợi ý cho lần sau</h2>
            <ul className="m-0 grid gap-2 pl-5 text-hud-body">
              {s.suggestions.map((x) => (
                <li key={x.code}>{suggestionText(x.code, x.minutes)}</li>
              ))}
            </ul>
            <p className="m-0 text-hud-label text-hud-ink-3">Đây là gợi ý từ số liệu của chuyến, không phải chẩn đoán.</p>
          </section>
        )}

        <section className="flex items-start gap-3 rounded-hud-sm bg-hud-surface p-4 ring-1 ring-hud-line">
          <Send aria-hidden className={`mt-0.5 size-5 shrink-0 ${delivery === "failed" ? "text-hud-caution" : "text-hud-system"}`} />
          <p className="m-0 text-hud-label text-hud-ink-2">{DELIVERY_TEXT[delivery]}</p>
        </section>

        <button
          type="button"
          onClick={onDone}
          className="inline-flex min-h-14 w-full items-center justify-center rounded-full border-0 bg-hud-ink px-6 text-hud-body font-semibold text-hud-bg sm:w-fit"
        >
          Xong
        </button>
      </main>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-hud bg-hud-surface p-4 ring-1 ring-hud-line">
      <div className="text-hud-label text-hud-ink-2">{label}</div>
      <div className="mt-1 text-hud-title font-bold tabular-nums">{value}</div>
    </div>
  );
}

/** One bar per minute, coloured by fatigue zone; stops are greyed. Plain words, no scores. */
function MinuteChart({ summary: s }: { summary: TripSummary }) {
  const n = Math.max(s.minutes.length, 1);
  const W = 600;
  const H = 120;
  const bw = W / n;
  return (
    <section className="grid gap-3 rounded-hud bg-hud-surface p-6 ring-1 ring-hud-line">
      <h2 className="m-0 text-hud-body font-semibold">Mức tỉnh táo theo từng phút</h2>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Mức tỉnh táo theo từng phút của chuyến" className="h-32 w-full" preserveAspectRatio="none">
        {s.minutes.map((m, i) => {
          const h = Math.max(6, (Math.min(m.drowsy_score, 100) / 100) * H);
          const zone = zoneOf(m.drowsy_score, s.score_l1, s.score_l2);
          return (
            <rect
              key={m.minute}
              x={i * bw + bw * 0.1}
              y={H - h}
              width={Math.max(bw * 0.8, 1)}
              height={h}
              rx={Math.min(3, bw * 0.3)}
              className={m.moving ? ZONE_FILL[zone] : "fill-hud-raised"}
            />
          );
        })}
      </svg>
      <div className="flex flex-wrap items-center gap-4 text-hud-label text-hud-ink-2">
        {(Object.keys(ZONE_TEXT) as Zone[]).map((z) => (
          <span key={z} className="inline-flex items-center gap-2">
            <span aria-hidden className={`size-3 rounded-full ${ZONE_DOT[z]}`} />
            {ZONE_TEXT[z]}
          </span>
        ))}
        <span className="inline-flex items-center gap-2">
          <span aria-hidden className="size-3 rounded-full bg-hud-raised" />
          Đang dừng
        </span>
        <span className="ml-auto">Từ lúc bắt đầu đến lúc kết thúc ({formatDuration(s.duration_s)})</span>
      </div>
    </section>
  );
}
