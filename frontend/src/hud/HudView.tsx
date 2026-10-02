// In-car HUD view (block 13): presentation only, every value comes in as props
// (HudScreen polls the edge agent, HudPreview feeds fixed scenarios). Design rules:
// - one glance (< 0.5 s): level colour + one icon + one action sentence fill the stage
// - the higher the level, the less on screen: L3 shows only the stop message
// - colour is never the only cue: level shape (circle, triangle, octagon) and text too
// - alerts appear in 150 ms, calm-down fades over 600 ms; L3 pulses at 1 Hz
// - at night L0-L1 are dimmed (no glare), L2-L3 always at full brightness
// - no L0-L3 codes for the driver: colour, shape and an action sentence (codes stay on the dashboard)
// - "Kết thúc chuyến" asks once more before ending (no accidental tap while driving)
// - driver enrollment starts only after the consent screen: why the face is enrolled, what happens
//   to the data, "Đồng ý" / "Để sau" (parked, never over an alert)
// - vehicle signals in their own strip under the top bar: blinking turn arrows, speed, parked /
//   driving, missing speed signal (hidden at L3 with everything else)
// - sound is always on; while the browser still blocks it, a full-width amber strip under the top
//   bar asks for one touch (on every screen, also L3 and the system screens)
import { useState } from "react";
import {
  Activity,
  ArrowBigLeft,
  ArrowBigRight,
  CameraOff,
  Car,
  UserRoundCog,
  CircleAlert,
  Coffee,
  Eye,
  EyeOff,
  Flag,
  FlagTriangleRight,
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
  UserCheck,
  TriangleAlert,
  Volume2,
  VolumeX,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
import { ago, clockText, formatNumber } from "../lib/format";
import {
  ENROLL_CONSENT,
  ENROLL_HINTS,
  ENROLL_STEPS,
  ENROLL_TEXT,
  LEVELS,
  REASON_ACTIONS,
  LOW_FPS_TEXT,
  SOUND_BLOCKED_TEXT,
  VEHICLE_SIGNAL_LOST_TEXT,
  SYSTEM_TEXT,
  reasonText,
} from "../lib/labels";
import type { EnrollStep, HudAlert, HudEnrollment, HudSnapshot, Level, Reason, VehicleAction } from "../lib/types";
import {
  ENROLL_STEP_ORDER,
  enrollReminder,
  enrollStep,
  isDistractionReason,
  isDrowsyReason,
  orderedReasons,
  showConsentPanel,
  showEnrollPanel,
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
  sound: boolean; // alert sound is playing; false while the browser still blocks it
  feedbackTarget: HudAlert | null; // newest alert the driver may still flag as false
  toast: string | null;
  edgeUrl: string;
  onEnableSound: () => void; // a touch that lifts the browser's sound block
  onToggleDemo: () => void;
  onFalseAlarm: () => void;
  onEndTrip?: () => void; // shown when the source can end the trip (live HUD, #/live)
  ending?: boolean;
  onVehicle?: (action: VehicleAction) => void; // "Đổi tài xế"
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
  error: CircleAlert,
  unavailable: ScanFace,
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
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [confirmDriver, setConfirmDriver] = useState(false);
  const showStrip = !system && !!snap && !danger;
  const soundBlocked = !props.sound;
  // Rows: top bar, [sound blocked], [vehicle strip], content.
  const rows = ["auto", ...(soundBlocked ? ["auto"] : []), ...(showStrip ? ["auto"] : []), "minmax(0,1fr)"];

  return (
    <div
      style={{ gridTemplateRows: rows.join(" ") }}
      className={`relative isolate grid min-h-dvh grid-cols-[minmax(0,1fr)] font-hud antialiased [color-scheme:dark] transition-colors ${speed} ${
        danger ? "bg-hud-danger text-white" : "bg-hud-bg text-hud-ink"
      }`}
    >
      {danger && (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 animate-hud-pulse bg-hud-danger-deep motion-reduce:hidden"
        />
      )}

      <TopBar
        {...props}
        danger={danger}
        className={`transition-opacity duration-700 ${dim}`}
        onAskEnd={props.onEndTrip ? () => setConfirmEnd(true) : undefined}
      />

      {soundBlocked && (
        <button
          type="button"
          role="alert"
          onClick={props.onEnableSound}
          className="flex min-h-16 w-full items-center justify-center gap-3 border-0 bg-hud-caution px-4 py-3 text-hud-body font-bold text-hud-on-warning"
        >
          <VolumeX aria-hidden className="size-7 shrink-0" />
          {SOUND_BLOCKED_TEXT}
        </button>
      )}

      {showStrip && snap && <VehicleStrip snap={snap} className={`transition-opacity duration-700 ${dim}`} />}

      {system || !snap ? (
        <SystemPanel state={system ?? "connecting"} edgeUrl={edgeUrl} />
      ) : (
        <main
          className={`grid gap-4 p-4 transition-opacity duration-700 sm:gap-6 sm:p-6 ${dim} ${
            danger ? "grid-rows-[minmax(0,1fr)]" : "lg:grid-cols-[minmax(0,2fr)_minmax(320px,1fr)] lg:grid-rows-[minmax(0,1fr)]"
          }`}
        >
          {showConsentPanel(snap.enrollment, level) ? (
            <ConsentPanel onAnswer={props.onVehicle} />
          ) : showEnrollPanel(snap.enrollment, level) && snap.enrollment ? (
            <EnrollPanel enrollment={snap.enrollment} />
          ) : (
            <StatusStage level={level} reasons={snap.reasons} eyesClosedS={snap.eyes_closed_s ?? 0} rising={rising} />
          )}
          {/* Hidden at L3: nothing to read or press while the driver must stop. */}
          {!danger && (
            <aside className="grid content-start gap-4 sm:grid-cols-2 sm:gap-6 lg:grid-cols-1">
              {props.onVehicle && (
                <VehicleCard
                  snap={snap}
                  onChangeDriver={() => setConfirmDriver(true)}
                />
              )}
              <EnrollReminder enrollment={snap.enrollment} />
              <MetricsCard snap={snap} level={level} />
              <FeedbackCard alerts={snap.alerts} target={feedbackTarget} now={now} onFalseAlarm={onFalseAlarm} />
            </aside>
          )}
        </main>
      )}

      {confirmDriver && props.onVehicle && (
        <ConfirmDialog
          title="Đổi tài xế?"
          text="Xe dừng lại. Người lái mới nhìn vào camera để đăng ký khuôn mặt, xong thì tiếp tục lái."
          cancel="Không đổi"
          confirm="Đổi tài xế"
          onCancel={() => setConfirmDriver(false)}
          onConfirm={() => {
            setConfirmDriver(false);
            props.onVehicle?.("change_driver");
          }}
        />
      )}

      {confirmEnd && props.onEndTrip && (
        <EndTripDialog
          ending={!!props.ending}
          onCancel={() => setConfirmEnd(false)}
          onConfirm={() => {
            setConfirmEnd(false);
            props.onEndTrip?.();
          }}
        />
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
  onEnableSound,
  onToggleDemo,
  onAskEnd,
  ending,
}: HudViewProps & { danger: boolean; className: string; onAskEnd?: () => void }) {
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

      {/* M28: too slow for a while, alerts may come late. */}
      {snap?.low_fps && snap.connected && (
        <span role="status" className={`inline-flex ${CHIP} bg-hud-caution text-hud-on-warning ring-transparent`}>
          <Hourglass aria-hidden className="size-5" />
          <span className="hidden sm:inline">{LOW_FPS_TEXT}</span>
        </span>
      )}
      {/* Sound is always on (no mute: alerts must be heard). Amber while the browser blocks it. */}
      {sound ? (
        <span role="img" aria-label="Âm thanh cảnh báo đang bật" className={`inline-flex ${CHIP} ${chip}`}>
          <Volume2 aria-hidden className="size-5" />
        </span>
      ) : (
        <button
          type="button"
          aria-label="Bật âm thanh cảnh báo"
          onClick={onEnableSound}
          className={`inline-flex ${CHIP} bg-hud-caution text-hud-on-warning ring-transparent`}
        >
          <VolumeX aria-hidden className="size-5" />
          <span className="hidden sm:inline">Bật âm thanh</span>
        </button>
      )}
      {/* End of trip: hidden at L3 (the driver must stop first, then end the trip). */}
      {onAskEnd && !danger && (
        <button
          type="button"
          onClick={onAskEnd}
          disabled={ending}
          aria-label="Kết thúc chuyến"
          className={`inline-flex ${CHIP} ${chip} disabled:opacity-50`}
        >
          <FlagTriangleRight aria-hidden className="size-5" />
          <span className="hidden sm:inline">{ending ? "Đang kết thúc…" : "Kết thúc chuyến"}</span>
        </button>
      )}
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
          {LEVELS[level].title}
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

// Guided driver enrollment: one instruction at a time, big, with the step's progress. The
// same words are spoken (HudScreen), since steps 2 and 3 are done without looking here.
// Before the enrollment steps: why, and what happens to the face data; the steps start on "Đồng ý".
function ConsentPanel({ onAnswer }: { onAnswer?: (action: VehicleAction) => void }) {
  return (
    <section
      aria-labelledby="consent-title"
      className="flex min-h-[52dvh] flex-col justify-center gap-6 rounded-hud-lg bg-hud-surface p-6 text-hud-ink ring-2 ring-hud-system sm:p-10 lg:min-h-0"
    >
      <span className="inline-flex w-fit items-center gap-2 rounded-full bg-hud-system/15 px-4 py-2 text-hud-label font-bold text-hud-system">
        <ScanFace aria-hidden className="size-5" strokeWidth={2.5} />
        {ENROLL_TEXT.title}
      </span>
      <div className="flex flex-col gap-3">
        <h1 id="consent-title" className="m-0 text-hud-display font-extrabold tracking-tight text-balance">
          {ENROLL_CONSENT.title}
        </h1>
        <p className="m-0 max-w-[60ch] text-hud-title font-medium text-hud-ink-2">{ENROLL_CONSENT.lead}</p>
      </div>
      <ul aria-label="Dữ liệu khuôn mặt của bạn" className="m-0 grid list-none gap-3 p-0">
        {ENROLL_CONSENT.privacy.map((line) => (
          <li key={line} className="flex items-start gap-3 text-hud-body text-hud-ink">
            <ShieldCheck aria-hidden className="mt-0.5 size-6 shrink-0 text-hud-safe" />
            <span>{line}</span>
          </li>
        ))}
      </ul>
      {onAnswer && (
        <div className="grid gap-3 sm:grid-cols-[2fr_1fr]">
          <button
            type="button"
            onClick={() => onAnswer("enroll_start")}
            className="min-h-16 rounded-full border-0 bg-hud-system px-6 text-hud-title font-bold text-hud-on-warning"
          >
            {ENROLL_CONSENT.agree}
          </button>
          <button
            type="button"
            onClick={() => onAnswer("enroll_later")}
            className="min-h-16 rounded-full border-0 bg-hud-raised px-6 text-hud-body font-semibold text-hud-ink ring-1 ring-hud-line"
          >
            {ENROLL_CONSENT.later}
          </button>
        </div>
      )}
      <p className="m-0 text-hud-label text-hud-ink-3">{ENROLL_CONSENT.laterNote}</p>
    </section>
  );
}

function EnrollPanel({ enrollment }: { enrollment: HudEnrollment }) {
  const step = enrollStep(enrollment) as EnrollStep;
  const index = ENROLL_STEP_ORDER.indexOf(step);
  const text = ENROLL_STEPS[step];
  const hint = enrollment.hint ? ENROLL_HINTS[enrollment.hint] : null;
  const pct = Math.round(Math.max(0, Math.min(1, enrollment.progress)) * 100);

  return (
    <section
      aria-live="polite"
      aria-atomic="true"
      className="relative flex min-h-[52dvh] flex-col justify-center gap-8 overflow-hidden rounded-hud-lg bg-hud-surface p-6 text-hud-ink ring-2 ring-hud-system sm:p-10 lg:min-h-0"
    >
      <div className="flex flex-wrap items-center gap-3">
        <span className="inline-flex items-center gap-2 rounded-full bg-hud-system/15 px-4 py-2 text-hud-label font-bold text-hud-system">
          <UserCheck aria-hidden className="size-5" strokeWidth={2.5} />
          {ENROLL_TEXT.title}
        </span>
        <ol aria-label="Các bước" className="m-0 flex list-none gap-2 p-0">
          {ENROLL_STEP_ORDER.map((s, i) => (
            <li
              key={s}
              aria-current={i === index ? "step" : undefined}
              className={`h-2 w-10 rounded-full ${i < index ? "bg-hud-safe" : i === index ? "bg-hud-system" : "bg-hud-raised"}`}
            >
              <span className="sr-only">
                Bước {i + 1}: {ENROLL_STEPS[s].title}
              </span>
            </li>
          ))}
        </ol>
        <span className="text-hud-label text-hud-ink-2 tabular-nums">
          Bước {index + 1}/{ENROLL_STEP_ORDER.length}
        </span>
      </div>

      {/* Re-mounted per step, so each new instruction animates in once. */}
      <div key={step} className="flex animate-hud-in-fast flex-col gap-3 motion-reduce:animate-none">
        <h1 className="m-0 text-hud-display font-extrabold tracking-tight text-balance">{text.title}</h1>
        <p className="m-0 text-hud-title font-medium text-hud-ink-2">{text.detail}</p>
      </div>

      <div>
        <div
          role="progressbar"
          aria-label={text.title}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={pct}
          className="h-3 overflow-hidden rounded-full bg-hud-raised"
        >
          <div
            className="h-full origin-left bg-hud-system transition-transform duration-300 ease-out"
            style={{ transform: `scaleX(${pct / 100})` }}
          />
        </div>
        <p className={`m-0 mt-4 min-h-[1.5em] text-hud-body font-semibold ${hint ? "text-hud-caution" : "text-hud-ink-3"}`}>
          {hint ?? "Giữ nguyên tư thế"}
        </p>
      </div>
    </section>
  );
}

function EnrollReminder({ enrollment }: { enrollment: HudEnrollment | undefined }) {
  const text = enrollReminder(enrollment);
  if (!text) return null;
  return (
    <section
      aria-label={ENROLL_TEXT.title}
      className="flex items-start gap-3 rounded-hud bg-hud-surface p-4 text-hud-label text-hud-ink-2 ring-1 ring-hud-line sm:col-span-2 lg:col-span-1"
    >
      <UserCheck aria-hidden className="mt-0.5 size-5 shrink-0 text-hud-system" />
      <span>{text}</span>
    </section>
  );
}

function MetricsCard({ snap, level }: { snap: HudSnapshot; level: Level }) {
  const bar = TONES[level].bar;
  const drowsy = level > 0 && snap.reasons.some(isDrowsyReason);
  const distracted = level > 0 && snap.reasons.some(isDistractionReason);

  return (
    <section aria-label="Thông số" className="flex flex-col gap-6 rounded-hud bg-hud-surface p-6 ring-1 ring-hud-line">
      {/* Speed lives in the vehicle strip above. */}
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
      {LEVELS[level].title}
    </span>
  );
}

function EndTripDialog({ ending, onCancel, onConfirm }: { ending: boolean; onCancel: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog
      title="Kết thúc chuyến đi?"
      text="Hệ thống ngừng theo dõi, hiện bản tổng kết chuyến và gửi cho quản lý đội xe."
      cancel="Tiếp tục lái"
      confirm="Kết thúc"
      busy={ending}
      onCancel={onCancel}
      onConfirm={onConfirm}
    />
  );
}

function ConfirmDialog({
  title,
  text,
  cancel,
  confirm,
  busy = false,
  onCancel,
  onConfirm,
}: {
  title: string;
  text: string;
  cancel: string;
  confirm: string;
  busy?: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div role="dialog" aria-modal="true" aria-labelledby="confirm-title" className="fixed inset-0 z-50 grid place-items-center bg-black/60 p-4">
      <div className="w-full max-w-md rounded-hud-lg bg-hud-surface p-6 text-hud-ink shadow-2xl ring-1 ring-hud-line">
        <h2 id="confirm-title" className="m-0 text-hud-title font-bold">
          {title}
        </h2>
        <p className="m-0 mt-2 text-hud-body text-hud-ink-2">{text}</p>
        <div className="mt-6 grid gap-3 sm:grid-cols-2">
          <button type="button" onClick={onCancel} className="min-h-14 rounded-full border-0 bg-hud-raised text-hud-body font-semibold text-hud-ink ring-1 ring-hud-line">
            {cancel}
          </button>
          <button type="button" onClick={onConfirm} disabled={busy} className="min-h-14 rounded-full border-0 bg-hud-system text-hud-body font-semibold text-hud-on-warning disabled:opacity-50">
            {confirm}
          </button>
        </div>
      </div>
    </div>
  );
}

// Vehicle strip: what the car says, readable at a glance. Turn arrows blink like the car's own
// indicator (static when the OS asks for reduced motion); the side that is on also widens how
// far the driver may look that way (block 8), so the strip says so.
function VehicleStrip({ snap, className }: { snap: HudSnapshot; className: string }) {
  const v = snap.vehicle;
  const speed = v ? v.speed_kmh : (snap.speed_kmh ?? 0); // null: link lost while driving, speed unknown
  const driving = v ? v.driving : (speed ?? 0) >= 1;
  const turn = v?.turn_signal ?? null;
  const lost = v?.signal_lost === true;
  const noSignal = v?.source === "sim" && !v.connected && !lost;
  return (
    <section
      aria-label="Tín hiệu xe"
      className={`flex items-center gap-3 border-b border-hud-line px-4 py-3 sm:gap-6 sm:px-6 ${className}`}
    >
      <TurnArrow side="left" on={turn === "left"} />
      <div className="flex min-w-0 flex-1 flex-wrap items-center justify-center gap-x-6 gap-y-2">
        <span className="inline-flex items-baseline gap-2">
          <span className="text-hud-metric font-bold tabular-nums">{speed == null ? "–" : Math.round(speed)}</span>
          <span className="text-hud-body text-hud-ink-2">km/h</span>
        </span>
        {driving ? (
          <span className="inline-flex items-center gap-2 rounded-full bg-hud-raised px-4 py-2 text-hud-body font-semibold ring-1 ring-hud-line">
            <Car aria-hidden className="size-6" /> Đang lái
          </span>
        ) : (
          <span className="inline-flex items-center gap-2 rounded-full bg-hud-raised px-4 py-2 text-hud-body font-semibold ring-1 ring-hud-line">
            <span aria-hidden className="grid size-7 place-items-center rounded-md bg-hud-system text-hud-label font-black text-hud-on-warning">
              P
            </span>
            Đang đỗ
          </span>
        )}
        {turn && (
          <span className="text-hud-body font-semibold text-hud-turn">
            Xi nhan {turn === "left" ? "trái" : "phải"} · được nhìn sang {turn === "left" ? "trái" : "phải"} nhiều hơn
          </span>
        )}
        {lost && (
          <span
            role="alert"
            className="inline-flex items-center gap-2 rounded-full bg-hud-caution px-4 py-2 text-hud-body font-bold text-hud-on-warning"
          >
            <WifiOff aria-hidden className="size-5" /> {VEHICLE_SIGNAL_LOST_TEXT[driving ? "driving" : "parked"]}
          </span>
        )}
        {noSignal && (
          <span className="inline-flex items-center gap-2 text-hud-body font-semibold text-hud-system">
            <WifiOff aria-hidden className="size-5" /> Chưa có tín hiệu xe: coi như đang đỗ
          </span>
        )}
      </div>
      <TurnArrow side="right" on={turn === "right"} />
    </section>
  );
}

function TurnArrow({ side, on }: { side: "left" | "right"; on: boolean }) {
  const Icon = side === "left" ? ArrowBigLeft : ArrowBigRight;
  return (
    <Icon
      role="img"
      aria-label={`Xi nhan ${side === "left" ? "trái" : "phải"}: ${on ? "đang bật" : "tắt"}`}
      className={`size-12 shrink-0 sm:size-16 ${
        on
          ? "fill-hud-turn text-hud-turn animate-hud-blink motion-reduce:animate-none"
          : "text-hud-ink-3 opacity-40"
      }`}
    />
  );
}

// Vehicle card: who is driving. Parked / driving is not a button: it follows the speed (strip
// above). Only "Đổi tài xế" is offered.
function VehicleCard({
  snap,
  onChangeDriver,
}: {
  snap: HudSnapshot;
  onChangeDriver: () => void;
}) {
  const v = snap.vehicle;
  const driving = v ? v.driving : (snap.speed_kmh ?? 0) >= 1;
  const enrolling = ["look_camera", "look_road", "close_eyes"].includes(snap.enrollment?.status ?? "");
  const btn =
    "inline-flex min-h-14 flex-1 items-center justify-center gap-2 whitespace-nowrap rounded-full border-0 px-4 text-hud-body font-semibold ring-1 transition active:scale-[0.98]";
  return (
    <section aria-label="Xe" className="flex flex-col gap-4 rounded-hud bg-hud-surface p-6 ring-1 ring-hud-line">
      <div className="flex items-center gap-3">
        <Car aria-hidden className={`size-6 ${driving ? "text-hud-safe" : "text-hud-ink-3"}`} />
        <span className="text-hud-body font-semibold">
          {driving ? "Đang lái" : enrolling ? "Xe đang đỗ · đang đăng ký khuôn mặt" : "Xe đang đỗ"}
        </span>
      </div>
      <div className="flex flex-wrap gap-3">
        <button type="button" onClick={onChangeDriver} className={`${btn} bg-hud-raised text-hud-ink ring-hud-line`}>
          <UserRoundCog aria-hidden className="size-5" /> Đổi tài xế
        </button>
      </div>
    </section>
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
          state === "camera_lost" || state === "unavailable" || state === "error" ? "ring-2 ring-hud-system" : "ring-1 ring-hud-line"
        }`}
      >
        <Icon
          aria-hidden
          strokeWidth={1.75}
          className={`mx-auto size-20 text-hud-system ${state === "connecting" ? "animate-spin motion-reduce:animate-none" : ""}`}
        />
        <h1 className="m-0 mt-6 text-[clamp(28px,4vw,48px)] leading-tight font-extrabold text-balance">{text.title}</h1>
        <p className="m-0 mt-3 text-hud-body text-pretty text-hud-ink-2">{text.detail}</p>
        {state !== "camera_lost" && state !== "unavailable" && state !== "error" && (
          <p className="m-0 mt-6 text-hud-label text-hud-ink-3">
            HUD đọc trạng thái từ edge agent tại <code className={code}>{edgeUrl}</code>. Chạy{" "}
            <code className={code}>python -m edge_agent.main --source 0</code> hoặc bấm “Chạy mô phỏng”.
          </p>
        )}
      </section>
    </main>
  );
}
