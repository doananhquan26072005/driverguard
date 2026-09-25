// In-car HUD view (block 13): presentation only, every value comes in as props
// (HudScreen polls the edge agent, HudPreview feeds fixed scenarios). Design rules:
// - one glance (< 0.5 s): level colour + one icon + one action sentence fill the stage
// - the higher the level, the less on screen: L3 shows only the stop message
// - colour is never the only cue: level shape (circle, triangle, octagon) and text too
// - alerts appear in 150 ms, calm-down fades over 600 ms; L3 pulses at 1 Hz
// - at night L0-L1 are dimmed (no glare), L2-L3 always at full brightness
import { useState } from "react";
import {
  Activity,
  CameraOff,
  CircleAlert,
  Coffee,
  Eye,
  EyeOff,
  Flag,
  Hourglass,
  LayoutDashboard,
  LoaderCircle,
  Moon,
  OctagonAlert,
  Play,
  ScanFace,
  ShieldCheck,
  Smartphone,
  Square,
  TrendingUp,
  TriangleAlert,
  Volume2,
  VolumeX,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
import { ago, clockText, formatNumber } from "../lib/format";
import { LEVELS, REASON_ACTIONS, SYSTEM_TEXT, reasonText } from "../lib/labels";
import type { HudAlert, HudSnapshot, Level, Reason } from "../lib/types";
import {
  isDistractionReason,
  isDrowsyReason,
  orderedReasons,
  systemState,
  type HudLink,
  type SystemState,
} from "./hudModel";

export interface HudViewProps {
  snap: HudSnapshot | null;
  link: HudLink;
  stale: boolean;
  cameraLost: boolean;
  demo: boolean;
  now: number; // seconds epoch
  sound: boolean;
  feedbackTarget: HudAlert | null; // newest alert the driver may still flag as false
  toast: string | null;
  edgeUrl: string;
  onToggleSound: () => void;
  onToggleDemo: () => void;
  onFalseAlarm: () => void;
}

interface Tone {
  stage: string; // status stage fill + text colour
  chip: string; // level chip on the stage
  icon: string; // big reason icon
  bar: string; // score bar of the branch that raised the alert
  badge: string; // small level badge on the dark surface
  LevelIcon: LucideIcon;
}

// Full class strings (Tailwind only generates classes it can find in the source).
const TONES: Record<Level, Tone> = {
  0: {
    stage: "bg-hud-surface text-hud-ink ring-1 ring-hud-line",
    chip: "bg-hud-safe/15 text-hud-safe",
    icon: "text-hud-safe",
    bar: "bg-hud-safe",
    badge: "bg-hud-safe text-hud-on-warning",
    LevelIcon: ShieldCheck,
  },
  1: {
    stage: "bg-hud-caution/10 text-hud-ink ring-2 ring-hud-caution",
    chip: "bg-hud-caution text-hud-on-warning",
    icon: "text-hud-caution",
    bar: "bg-hud-caution",
    badge: "bg-hud-caution text-hud-on-warning",
    LevelIcon: CircleAlert,
  },
  2: {
    stage: "bg-hud-warning text-hud-on-warning ring-0",
    chip: "bg-hud-on-warning/15 text-hud-on-warning",
    icon: "text-hud-on-warning",
    bar: "bg-hud-warning",
    badge: "bg-hud-warning text-hud-on-warning",
    LevelIcon: TriangleAlert,
  },
  3: {
    stage: "bg-transparent text-white ring-0", // the whole screen is red (see HudView)
    chip: "bg-black/25 text-white",
    icon: "text-white",
    bar: "bg-hud-danger",
    badge: "bg-hud-danger text-white",
    LevelIcon: OctagonAlert,
  },
};

const REASON_ICONS: Partial<Record<Reason, LucideIcon>> = {
  microsleep: EyeOff,
  drowsy_score: Coffee,
  trend: TrendingUp,
  blink_rate: Activity,
  off_road: Eye,
  phone: Smartphone,
  no_face: ScanFace,
};

const SYSTEM_ICONS: Record<SystemState, LucideIcon> = {
  down: WifiOff,
  camera_lost: CameraOff,
  stale: Hourglass,
  connecting: LoaderCircle,
};

// No Tailwind preflight (the dashboard keeps styles.css), so buttons need border-0 themselves.
// Display is set per chip, so a chip can be hidden on small screens.
const CHIP =
  "min-h-12 min-w-12 items-center justify-center gap-2 rounded-full border-0 px-3 text-hud-label font-semibold whitespace-nowrap no-underline ring-1 transition-colors lg:px-4";

/** True when the last level change went up: alerts snap in, calming down fades slowly. */
function useRising(level: Level): boolean {
  const [prev, setPrev] = useState(level);
  const [rising, setRising] = useState(true);
  if (level !== prev) {
    setPrev(level);
    setRising(level > prev);
  }
  return rising;
}

export default function HudView(props: HudViewProps) {
  const { snap, link, stale, cameraLost, now, feedbackTarget, toast, edgeUrl, onFalseAlarm } = props;
  const system = systemState(link, snap, stale, cameraLost);
  const level: Level = system || !snap ? 0 : snap.level;
  const rising = useRising(level);
  const danger = level === 3;
  const dim = !system && !!snap?.night && level <= 1 ? "opacity-80" : "";
  const speed = rising ? "duration-150" : "duration-700";

  return (
    <div
      className={`relative isolate grid min-h-dvh grid-cols-[minmax(0,1fr)] grid-rows-[auto_minmax(0,1fr)] font-hud antialiased [color-scheme:dark] transition-colors ${speed} ${
        danger ? "bg-hud-danger text-white" : "bg-hud-bg text-hud-ink"
      }`}
    >
      {danger && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 animate-hud-pulse bg-hud-danger-deep motion-reduce:hidden"
        />
      )}

      <TopBar {...props} danger={danger} className={`transition-opacity duration-700 ${dim}`} />

      {system || !snap ? (
        <SystemPanel state={system ?? "connecting"} edgeUrl={edgeUrl} />
      ) : (
        <main
          className={`grid gap-4 p-4 transition-opacity duration-700 sm:gap-6 sm:p-6 ${dim} ${
            danger ? "grid-rows-[minmax(0,1fr)]" : "lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)] lg:grid-rows-[minmax(0,1fr)]"
          }`}
        >
          <StatusStage level={level} reasons={snap.reasons} eyesClosedS={snap.eyes_closed_s ?? 0} rising={rising} />
          {/* Hidden at L3: nothing to read or press while the driver must stop. */}
          {!danger && (
            <aside className="grid content-start gap-4 sm:grid-cols-2 sm:gap-6 lg:grid-cols-1">
              <MetricsCard snap={snap} level={level} />
              <FeedbackCard alerts={snap.alerts} target={feedbackTarget} now={now} onFalseAlarm={onFalseAlarm} />
            </aside>
          )}
        </main>
      )}

      {toast && (
        <div
          role="status"
          className="fixed inset-x-4 bottom-6 z-50 mx-auto w-fit animate-hud-in-fast rounded-hud-sm bg-hud-raised px-6 py-4 text-hud-body text-hud-ink shadow-2xl ring-1 ring-white/15"
        >
          {toast}
        </div>
      )}
    </div>
  );
}

function TopBar({
  snap,
  link,
  demo,
  sound,
  danger,
  className,
  onToggleSound,
  onToggleDemo,
}: HudViewProps & { danger: boolean; className: string }) {
  const chip = danger ? "bg-black/20 text-white ring-white/30" : "bg-hud-surface text-hud-ink-2 ring-hud-line";
  const [dot, status] = demo
    ? ["bg-hud-system", "Mô phỏng"]
    : link === "ok"
      ? ["bg-hud-safe", "Đã kết nối"]
      : link === "down"
        ? ["ring-2 ring-inset ring-current", "Mất kết nối"]
        : ["bg-hud-ink-3 animate-pulse", "Đang kết nối…"];

  return (
    <header
      className={`flex items-center gap-2 border-b px-4 py-2 sm:gap-3 sm:px-6 ${danger ? "border-white/20" : "border-hud-line"} ${className}`}
    >
      <span className="text-hud-label font-bold tracking-tight">DriverGuard</span>
      <span role="status" className={`inline-flex items-center gap-2 text-hud-label whitespace-nowrap ${danger ? "" : "text-hud-ink-2"}`}>
        <span aria-hidden className={`size-2.5 rounded-full ${dot}`} />
        <span className="sr-only sm:not-sr-only">{status}</span>
      </span>

      <span className="ml-auto inline-flex items-center gap-2 text-hud-body font-semibold tabular-nums">
        {snap?.night && <Moon aria-label="Ban đêm" className="size-5 opacity-70" />}
        {clockText(snap?.clock_hour)}
      </span>

      {/* Sound off is unsafe: the chip turns amber until the driver enables it. */}
      <button
        type="button"
        aria-label="Âm thanh cảnh báo"
        aria-pressed={sound}
        onClick={onToggleSound}
        className={`inline-flex ${CHIP} ${sound ? chip : "bg-hud-caution text-hud-on-warning ring-transparent"}`}
      >
        {sound ? <Volume2 aria-hidden className="size-5" /> : <VolumeX aria-hidden className="size-5" />}
        <span className="hidden sm:inline">{sound ? "Âm thanh" : "Bật âm thanh"}</span>
      </button>
      {/* Not needed while driving: hidden at L3 and on phones. */}
      {!danger && (
        <>
          <button
            type="button"
            aria-label={demo ? "Về thiết bị thật" : "Chạy mô phỏng"}
            onClick={onToggleDemo}
            className={`hidden sm:inline-flex ${CHIP} ${chip}`}
          >
            {demo ? <Square aria-hidden className="size-5" /> : <Play aria-hidden className="size-5" />}
            <span className="hidden lg:inline">{demo ? "Về thiết bị thật" : "Chạy mô phỏng"}</span>
          </button>
          <a href="#/dashboard" aria-label="Dashboard" className={`inline-flex ${CHIP} ${chip}`}>
            <LayoutDashboard aria-hidden className="size-5" />
            <span className="hidden lg:inline">Dashboard</span>
          </a>
        </>
      )}
    </header>
  );
}

function StatusStage({
  level,
  reasons,
  eyesClosedS,
  rising,
}: {
  level: Level;
  reasons: Reason[];
  eyesClosedS: number;
  rising: boolean;
}) {
  const tone = TONES[level];
  const ordered = orderedReasons(reasons);
  const primary = level > 0 ? (ordered[0] ?? null) : null;
  const Icon = (primary && REASON_ICONS[primary]) || tone.LevelIcon;
  const headline = primary
    ? REASON_ACTIONS[primary]
    : level === 0
      ? "Tỉnh táo"
      : level === 3
        ? LEVELS[3].action
        : LEVELS[level].title;
  const detail = level === 0 ? "Tiếp tục lái an toàn" : ordered.map(reasonText).join(" · ");
  const center = level === 3;

  return (
    <section
      aria-live="assertive"
      aria-atomic="true"
      className={`relative flex min-h-[52dvh] flex-col justify-center overflow-hidden rounded-hud-lg p-6 transition-[background-color,color,box-shadow] sm:p-10 lg:min-h-0 ${
        rising ? "duration-150" : "duration-700"
      } ${tone.stage} ${center ? "items-center text-center" : ""}`}
    >
      {/* Re-mounted on every level / reason change, so the enter animation plays once per alert.
          The live region is the section above: it stays mounted, so screen readers announce the change. */}
      <div
        key={`${level}:${primary ?? ""}`}
        className={`flex flex-col gap-6 motion-reduce:animate-none ${rising ? "animate-hud-in-fast" : "animate-hud-in-slow"} ${
          center ? "items-center" : "items-start"
        }`}
      >
        <span className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-hud-label font-bold ${tone.chip}`}>
          <tone.LevelIcon aria-hidden className="size-5" strokeWidth={2.5} />
          {LEVELS[level].short} · {LEVELS[level].title}
        </span>
        <div className={`flex gap-6 sm:gap-8 ${center ? "flex-col items-center" : "flex-col sm:flex-row sm:items-center"}`}>
          <Icon aria-hidden strokeWidth={1.75} className={`size-20 shrink-0 sm:size-28 ${center ? "lg:size-40" : ""} ${tone.icon}`} />
          <div className="min-w-0">
            <h1 className="m-0 text-hud-display font-extrabold tracking-tight text-balance">{headline}</h1>
            {detail && <p className="m-0 mt-3 text-hud-title font-medium opacity-85">{detail}</p>}
          </div>
        </div>
      </div>

      {center && eyesClosedS > 0 && (
        <p aria-hidden className="m-0 mt-10 rounded-full bg-black/25 px-6 py-3 text-hud-title font-semibold tabular-nums">
          Mắt nhắm {formatNumber(eyesClosedS, 1)} giây
        </p>
      )}
    </section>
  );
}

function MetricsCard({ snap, level }: { snap: HudSnapshot; level: Level }) {
  const bar = TONES[level].bar;
  const drowsy = level > 0 && snap.reasons.some(isDrowsyReason);
  const distracted = level > 0 && snap.reasons.some(isDistractionReason);

  return (
    <section aria-label="Thông số" className="flex flex-col gap-6 rounded-hud bg-hud-surface p-6 ring-1 ring-hud-line">
      <div>
        <div className="text-hud-label text-hud-ink-2">Tốc độ</div>
        <div className="mt-1 flex items-baseline gap-2">
          <span className="text-hud-metric font-bold tabular-nums">{formatNumber(snap.speed_kmh ?? null)}</span>
          <span className="text-hud-label text-hud-ink-2">km/h</span>
        </div>
      </div>
      <ScoreBar label="Buồn ngủ" value={snap.drowsy_score} fill={drowsy ? bar : "bg-hud-ink-3"} />
      <ScoreBar label="Mất tập trung" value={snap.distraction_score} fill={distracted ? bar : "bg-hud-ink-3"} />
      <div className="flex items-baseline justify-between">
        <span className="text-hud-label text-hud-ink-2">Mắt nhắm</span>
        <span className="text-hud-body font-semibold tabular-nums">
          {formatNumber(snap.eyes_closed_s, 1)} <span className="text-hud-label font-medium text-hud-ink-3">giây</span>
        </span>
      </div>
    </section>
  );
}

function ScoreBar({ label, value, fill }: { label: string; value: number | undefined; fill: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="text-hud-label text-hud-ink-2">{label}</span>
        <span className="text-hud-body font-semibold tabular-nums">
          {formatNumber(value)}
          <span className="text-hud-label font-medium text-hud-ink-3">/100</span>
        </span>
      </div>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={v}
        className="mt-2 h-2 overflow-hidden rounded-full bg-hud-raised"
      >
        {/* scaleX, not width: animates on the compositor, no layout every 300 ms poll */}
        <div
          className={`h-full origin-left transition-[transform,background-color] duration-300 ease-out ${fill}`}
          style={{ transform: `scaleX(${v / 100})` }}
        />
      </div>
    </div>
  );
}

function FeedbackCard({
  alerts,
  target,
  now,
  onFalseAlarm,
}: {
  alerts: HudAlert[];
  target: HudAlert | null;
  now: number;
  onFalseAlarm: () => void;
}) {
  const last = alerts[0];
  const note = !last
    ? "Chưa có cảnh báo nào"
    : last.feedback
      ? "Đã ghi nhận: đây là cảnh báo sai"
      : target
        ? null
        : "Đã hết thời gian báo sai";

  return (
    <section aria-label="Phản hồi cảnh báo" className="flex flex-col gap-4 rounded-hud bg-hud-surface p-6 ring-1 ring-hud-line">
      {last && (
        <div>
          <div className="text-hud-label text-hud-ink-2">
            Cảnh báo gần nhất · <span className="tabular-nums">{ago(now - last.at)}</span>
          </div>
          <div className="mt-2 flex items-center gap-3 text-hud-body font-semibold">
            <LevelBadge level={last.level} />
            <span className="min-w-0">{last.reasons.map(reasonText).join(", ") || LEVELS[last.level].title}</span>
          </div>
        </div>
      )}
      {target ? (
        <button
          type="button"
          onClick={onFalseAlarm}
          className="flex min-h-16 w-full items-center justify-center gap-3 rounded-hud-sm border-0 bg-hud-raised text-hud-body font-semibold text-hud-ink ring-1 ring-hud-line transition hover:bg-white/10 active:scale-[0.98]"
        >
          <Flag aria-hidden className="size-6" />
          Cảnh báo sai
        </button>
      ) : (
        <p className="m-0 text-hud-label text-hud-ink-3">{note}</p>
      )}
    </section>
  );
}

function LevelBadge({ level }: { level: Level }) {
  const { badge, LevelIcon } = TONES[level];
  return (
    <span className={`inline-flex shrink-0 items-center gap-1 rounded-full px-2.5 py-1 text-hud-label font-bold ${badge}`}>
      <LevelIcon aria-hidden className="size-4" strokeWidth={2.5} />
      {LEVELS[level].short}
    </span>
  );
}

function SystemPanel({ state, edgeUrl }: { state: SystemState; edgeUrl: string }) {
  const Icon = SYSTEM_ICONS[state];
  const text = SYSTEM_TEXT[state];
  const code = "rounded bg-hud-raised px-1.5 py-0.5 text-hud-ink";
  return (
    <main className="grid place-items-center p-4 sm:p-6">
      <section
        aria-live="polite"
        className={`w-full max-w-2xl rounded-hud-lg bg-hud-surface p-8 text-center sm:p-12 ${
          state === "camera_lost" ? "ring-2 ring-hud-system" : "ring-1 ring-hud-line"
        }`}
      >
        <Icon
          aria-hidden
          strokeWidth={1.75}
          className={`mx-auto size-20 text-hud-system ${state === "connecting" ? "animate-spin motion-reduce:animate-none" : ""}`}
        />
        <h1 className="m-0 mt-6 text-[clamp(28px,4vw,48px)] leading-tight font-extrabold text-balance">{text.title}</h1>
        <p className="m-0 mt-3 text-hud-body text-pretty text-hud-ink-2">{text.detail}</p>
        {state !== "camera_lost" && (
          <p className="m-0 mt-6 text-hud-label text-hud-ink-3">
            HUD đọc trạng thái từ edge agent tại <code className={code}>{edgeUrl}</code>. Chạy{" "}
            <code className={code}>python -m edge_agent.main --source 0</code> hoặc bấm “Chạy mô phỏng”.
          </p>
        )}
      </section>
    </main>
  );
}
