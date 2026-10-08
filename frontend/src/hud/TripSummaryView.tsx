// End-of-trip screen for the driver (after "Kết thúc chuyến"), on the 1280 x 800 HUD stage of the redesign
// (M58, design "Tổng kết chuyến đi"): the assessment card in the trip's colour with its plain-language
// story, four facts, the fatigue of the whole trip (at most 65 bars, stops greyed), suggestions as tiles,
// and where the summary went. No variable names, no L0-L3: the engineer version is on the dashboard.
import {
  Bell,
  CircleAlert,
  CircleCheck,
  Coffee,
  Eye,
  Flag,
  OctagonAlert,
  ScanFace,
  Send,
  Smartphone,
  Timer,
  Video,
  type LucideIcon,
} from "lucide-react";
import { hourMinute } from "../lib/format";
import type { SuggestionCode, TripDelivery, TripRating, TripSummary } from "../lib/types";
import HudStage from "./HudStage";
import {
  DELIVERY_TEXT,
  RATING_REASON_TEXT,
  RATING_TEXT,
  driverStory,
  formatDuration,
  suggestionTile,
  summaryBars,
  type Zone,
} from "./tripModel";

const RATING_TONE: Record<TripRating, { card: string; dot: string; icon: string; sub: string; Icon: LucideIcon }> = {
  good: { card: "l0", dot: "var(--good)", icon: "text-hud-safe", sub: "text-[#bbd9c4]", Icon: CircleCheck },
  attention: { card: "l1", dot: "var(--warning)", icon: "text-hud-caution", sub: "text-[#e5d3a6]", Icon: CircleAlert },
  risk: { card: "l3t", dot: "#f87171", icon: "text-[#f87171]", sub: "text-[#f3c4c4]", Icon: OctagonAlert },
};

const ZONE_COLOR: Record<Zone, string> = { awake: "#4ade80", tired: "#fbbf24", very_tired: "#f87171" };
const LEGEND: [string, string][] = [
  ["#4ade80", "Tỉnh táo"],
  ["#fbbf24", "Mệt"],
  ["#f87171", "Rất mệt"],
  ["rgba(255,255,255,0.25)", "Xe dừng"],
];

const SUGGESTION_ICON: Record<SuggestionCode, LucideIcon> = {
  rest_now: Coffee,
  rest_after: Coffee,
  regular_breaks: Timer,
  phone_away: Smartphone,
  eyes_on_road: Eye,
  check_camera: Video,
  enroll: ScanFace,
};

interface Props {
  summary: TripSummary;
  delivery: TripDelivery;
  onDone: () => void;
}

const epoch = (iso: string) => Date.parse(iso) / 1000;
const dayText = (iso: string) => {
  const d = new Date(iso);
  const weekday = new Intl.DateTimeFormat("vi-VN", { weekday: "long" }).format(d);
  return `${weekday.charAt(0).toUpperCase()}${weekday.slice(1)} ${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
};

export default function TripSummaryView({ summary: s, delivery, onDone }: Props) {
  const tone = RATING_TONE[s.rating];
  const rating = RATING_TEXT[s.rating];
  const reminders = Object.values(s.alerts_by_reason).reduce((a, b) => a + (b ?? 0), 0);
  const reasons = s.rating_reasons.filter((r) => r !== "low_coverage" || s.rating === "good");
  const span = `${hourMinute(epoch(s.started_at))} – ${hourMinute(epoch(s.ended_at))}`;

  return (
    <HudStage rows={["72px", "minmax(0,1fr)", "auto"]} className="bg-hud-bg text-hud-ink">
      <header className="flex items-center px-4 hud-sm:px-8">
        <span className="flex flex-col gap-0.5">
          <span className="text-[17px] font-semibold tracking-[0.12em]">DRIVERGUARD</span>
          <span className="dg-num text-xs text-hud-ink-3">Tổng kết chuyến đi · {span}</span>
        </span>
      </header>

      <main className="grid min-h-0 gap-3.5 px-4 hud-sm:px-8 hud-lg:grid-cols-[450px_minmax(0,1fr)]">
        <div className="flex min-h-0 flex-col gap-3.5">
          <section aria-live="polite" className={`dg-alert ${tone.card} flex flex-col gap-[18px] px-[26px] py-6`}>
            <div className="flex items-start justify-between gap-3">
              <span className="dg-card-title">
                <b>Đánh giá chuyến</b>
                <span>{dayText(s.started_at)}</span>
              </span>
              <span className="dg-chip" style={{ ["--dot" as string]: tone.dot }}>
                <i />
                {rating.title}
              </span>
            </div>
            <div className="flex items-center gap-[18px]">
              <div className={`dg-tile grid size-[72px] shrink-0 place-items-center !rounded-[18px] ${tone.icon}`}>
                <tone.Icon aria-hidden className="size-9" strokeWidth={1.75} />
              </div>
              <div className="min-w-0">
                <h1 className="m-0 text-[clamp(30px,3.2vw,40px)] leading-[1.05] font-semibold tracking-[-0.03em]">{rating.title}</h1>
                <p className={`m-0 mt-1.5 text-[15px] ${tone.sub}`}>{rating.detail}</p>
              </div>
            </div>
            <p className="m-0 text-base leading-relaxed text-[#e8e1d0]">{driverStory(s)}</p>
            {reasons.length > 0 && (
              <ul className="m-0 grid gap-1 pl-5 text-[13px] text-hud-ink-2">
                {reasons.map((r) => (
                  <li key={r}>{RATING_REASON_TEXT[r]}</li>
                ))}
              </ul>
            )}
          </section>

          <section aria-label="Số liệu chính" className="grid grid-cols-2 gap-2.5">
            <Fact icon={Timer} value={formatDuration(s.driving_s)} label="Thời gian lái" />
            <Fact icon={Coffee} value={String(s.rests)} label="Lần nghỉ" />
            <Fact icon={Bell} value={String(reminders)} label="Lần nhắc nhở" />
            <Fact icon={Flag} value={String(s.false_alarms)} label="Bạn đã báo sai" />
          </section>
        </div>

        <div className="flex min-h-0 flex-col gap-3.5">
          <MinuteChart summary={s} />
          {s.suggestions.length > 0 && (
            <section className="dg-card flex min-h-0 flex-1 flex-col gap-3 px-6 py-[22px]">
              <span className="dg-card-title">
                <b>Gợi ý cho lần sau</b>
                <span>Từ số liệu của chuyến, không phải chẩn đoán</span>
              </span>
              <div className="grid gap-2.5 hud-sm:grid-cols-2">
                {s.suggestions.map((x, i) => {
                  const tile = suggestionTile(x.code, x.minutes);
                  return (
                    <Fact
                      key={x.code}
                      icon={SUGGESTION_ICON[x.code]}
                      value={tile.value}
                      label={tile.label}
                      accent={i === 0 ? tone.icon : undefined}
                    />
                  );
                })}
              </div>
            </section>
          )}
        </div>
      </main>

      <footer className="grid items-center gap-3.5 px-4 pt-3.5 pb-5 hud-sm:grid-cols-[minmax(0,1fr)_230px] hud-sm:px-8">
        <span className="flex items-center gap-2.5 text-[15px] text-hud-ink-2">
          <Send aria-hidden className={`size-[18px] shrink-0 ${delivery === "failed" ? "text-hud-caution" : "text-[#93c5fd]"}`} />
          {DELIVERY_TEXT[delivery]}
        </span>
        <button
          type="button"
          onClick={onDone}
          className="h-14 cursor-pointer rounded-hud-sm border-0 bg-[linear-gradient(180deg,#ffffff_0%,#dadada_100%)] text-[17px] font-semibold text-hud-bg"
        >
          Xong
        </button>
      </footer>
    </HudStage>
  );
}

function Fact({ icon: Icon, value, label, accent }: { icon: LucideIcon; value: string; label: string; accent?: string }) {
  return (
    <div className="dg-tile flex min-w-0 items-center gap-3 p-3">
      <span className={`dg-tile grid size-[38px] shrink-0 place-items-center !rounded-[10px] ${accent ?? "text-[#d4d4d4]"}`}>
        <Icon aria-hidden className="size-[18px]" />
      </span>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="dg-num text-[17px] font-medium">{value}</span>
        <span className="text-xs text-hud-ink-3">{label}</span>
      </span>
    </div>
  );
}

/** The whole trip, a few minutes per bar, coloured by fatigue zone; stops are greyed. Plain words, no scores. */
function MinuteChart({ summary: s }: { summary: TripSummary }) {
  const { perBar, bars } = summaryBars(s);
  const start = epoch(s.started_at);
  const end = epoch(s.ended_at);
  return (
    <section aria-label="Độ mệt theo từng phút" className="dg-card flex flex-col gap-3.5 px-6 py-[22px]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <span className="dg-card-title">
          <b>Độ mệt theo từng phút</b>
          <span>
            {perBar} phút mỗi cột · cả chuyến ({formatDuration(s.duration_s)})
          </span>
        </span>
        <span className="flex flex-wrap gap-3.5 text-xs text-hud-ink-2">
          {LEGEND.map(([color, text]) => (
            <span key={text} className="inline-flex items-center gap-1.5">
              <span aria-hidden className="size-2 rounded-full" style={{ background: color }} />
              {text}
            </span>
          ))}
        </span>
      </div>
      <div
        role="img"
        aria-label={`Độ mệt theo thời gian của chuyến${s.first_tired_min != null ? `: có dấu hiệu mệt từ phút lái thứ ${s.first_tired_min}` : ""}`}
        className="flex h-[150px] items-end gap-[3px] border-0 border-b border-solid border-white/8"
      >
        {bars.map((b, i) => (
          <div
            key={i}
            className="flex-1 rounded-t-[2px]"
            style={{
              height: `${b.stopped ? 4 : Math.max(4, Math.min(100, b.score))}%`,
              background: b.stopped ? "rgba(255,255,255,0.12)" : ZONE_COLOR[b.zone],
            }}
          />
        ))}
      </div>
      <div className="dg-num flex justify-between text-xs text-hud-ink-3">
        <span>{hourMinute(start)}</span>
        <span>{hourMinute((start + end) / 2)}</span>
        <span>{hourMinute(end)}</span>
      </div>
    </section>
  );
}
