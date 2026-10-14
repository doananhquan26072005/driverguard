// In-car HUD view (block 13): presentation only, every value comes in as props
// (HudScreen polls the edge agent, HudPreview feeds fixed scenarios). Version 4 redesign (M58), on
// the DriverGuard design system (dark ground, glass cards lit from the top left, Inter):
// - one glance (< 0.5 s): level colour + level shape + one action sentence
// - the higher the level, the less on screen: L0 has the fatigue chart, L2 drops it, L3 is only the
//   stop order on a red screen (no card, no button)
// - colour is never the only cue: circle with a tick (L0), circle "!" (L1), triangle (L2), octagon (L3)
// - alerts appear in 150 ms, calm-down fades over 600 ms; L3 pulses at 1 Hz
// - in the dark hours (snap.dim: hud.dim_hours, not the score's night window) L0-L1 are dimmed (no
//   glare), L2-L3 always at full brightness
// - no L0-L3 codes for the driver (codes stay on the dashboard)
// - the trip numbers (continuous driving, the last minutes' fatigue, an alert's detail) come from the
//   agent (M65), so a reload shows them again at once; nothing here counts them
// - "Kết thúc chuyến" and "Đổi tài xế" ask once more (no accidental tap while driving)
// - nothing on the screen stops or hides the monitoring with one touch (M72): the demo button and the
//   Dashboard link are there only while no device is watched (hudModel.hudCanLeave)
// - sound is always on; while the browser still blocks it, an amber strip under the top bar asks for
//   one touch (on every screen, also L3 and the system screens)
// Enrollment, consent, presence and system screens keep their M57 look inside this frame until M59.
import { useState } from "react";
import {
  Activity,
  ArrowBigLeft,
  ArrowBigRight,
  Cable,
  Camera,
  CameraOff,
  Check,
  ChevronRight,
  CircleAlert,
  Clock,
  Coffee,
  Eye,
  EyeOff,
  Flag,
  FlagTriangleRight,
  Hand,
  History,
  Hourglass,
  LayoutDashboard,
  LoaderCircle,
  Navigation,
  Moon,
  OctagonAlert,
  PhoneOff,
  Play,
  ScanFace,
  Send,
  ShieldCheck,
  Smartphone,
  Square,
  TrendingUp,
  TriangleAlert,
  UserRoundCog,
  Volume2,
  VolumeX,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
import { HUD_DEFAULTS } from "../lib/defaults";
import { clockText, durationText, formatNumber, hourMinute } from "../lib/format";
import {
  ENROLL_CONSENT,
  ENROLL_HINTS,
  ENROLL_STEPS,
  LEVELS,
  LOW_FPS_TEXT,
  PHONE_UNAVAILABLE_TEXT,
  PRESENCE_TEXT,
  REASON_ACTIONS,
  REASON_SHORT,
  SOUND_BLOCKED_TEXT,
  SYSTEM_TEXT,
  UNAVAILABLE_CAUSES,
  VEHICLE_SIGNAL_LOST_TEXT,
  reasonText,
} from "../lib/labels";
import type { EnrollStep, HudAlert, HudEnrollment, HudSnapshot, Level, Reason, VehicleAction } from "../lib/types";
import { NO_VIETNAMESE_VOICE_TEXT, useVietnameseVoice } from "./voice";
import FaceGuide from "./FaceGuide";
import HudStage from "./HudStage";
import {
  ENROLL_STEP_ORDER,
  alertDetail,
  attentionWord,
  drowsyWord,
  eyesWord,
  enrollReminder,
  enrollStep,
  footerNote,
  orderedReasons,
  presenceUp,
  showConsentPanel,
  showEnrollPanel,
  splitAction,
  hudDimmed,
  systemState,
  trendSlots,
  type Tone,
  type TrendSlot,
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
  onToggleDemo?: () => void; // absent: no demo button and no Dashboard link (a driver is watched, M72)
  askEnd?: number; // a new number opens the "Kết thúc ca lái" question (#/live's "Dừng camera", M72)
  onFalseAlarm: () => void;
  onEndTrip?: () => void; // shown when the source can end the trip (live HUD, #/live)
  ending?: boolean;
  onVehicle?: (action: VehicleAction) => void; // "Đổi tài xế"
  camera?: MediaStream | null; // #/live: the page's own camera, for the enrollment frame
}

const REASON_ICONS: Partial<Record<Reason, LucideIcon>> = {
  microsleep: EyeOff,
  unresponsive: EyeOff,
  repeated_l3: EyeOff,
  drowsy_score: Coffee,
  trend: TrendingUp,
  blink_rate: Activity,
  off_road: Eye,
  phone: Smartphone,
  no_face: ScanFace,
};



// Small glass square of the top bar (camera, sound, demo, dashboard): 40 px, icon only.
// No display here: each use says inline-grid or hidden hud-sm:inline-grid (two display classes would clash).
const TOP_TILE = "dg-tile size-10 shrink-0 place-items-center text-[#bdbdbd] no-underline";
// Amber outlined note of the top bar (slow machine, phone detector down).
const TOP_NOTE =
  "inline-flex h-10 items-center gap-2 rounded-[8px] border border-solid border-hud-caution/45 bg-hud-caution/12 px-3.5 text-sm font-medium whitespace-nowrap text-[#fcd34d]";

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

const isDriving = (snap: HudSnapshot) => (snap.vehicle ? snap.vehicle.driving : (snap.speed_kmh ?? 0) >= 1);

export default function HudView(props: HudViewProps) {
  const { snap, link, stale, cameraLost, now, feedbackTarget, toast, edgeUrl, onFalseAlarm } = props;
  const system = systemState(link, snap, stale, cameraLost);
  const level: Level = system || !snap ? 0 : snap.level;
  const rising = useRising(level);
  const danger = level === 3;
  const dim = hudDimmed(snap, level, system) ? "opacity-80" : "";
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [confirmDriver, setConfirmDriver] = useState(false);
  const [askedEnd, setAskedEnd] = useState(props.askEnd ?? 0);
  if ((props.askEnd ?? 0) !== askedEnd) {
    setAskedEnd(props.askEnd ?? 0);
    setConfirmEnd(true);
  }
  const soundBlocked = !props.sound;
  const presence = presenceUp(system, snap);
  // Rows: top bar, [sound blocked], content, bottom bar.
  const rows = ["72px", ...(soundBlocked ? ["auto"] : []), "minmax(0,1fr)", "auto"];
  const ring = !system && level === 1 ? "dg-ring-1" : !system && level === 2 ? "dg-ring-2" : "";

  const consent = !system && !!snap && showConsentPanel(snap.enrollment, level);
  const enrolling = !system && !!snap && !consent && showEnrollPanel(snap.enrollment, level) && !!snap.enrollment;
  const dashboard = !consent && !enrolling && level <= 1; // status + fatigue cards, speed card on two rows

  return (
    <HudStage
      rows={rows}
      style={danger ? { background: "radial-gradient(120% 100% at 50% 40%, #ef4444 0%, #dc2626 45%, #991b1b 100%)" } : undefined}
      className={`transition-shadow ${rising ? "duration-150" : "duration-700"} ${danger ? "text-white" : "bg-hud-bg text-hud-ink"} ${ring}`}
      underlay={
        danger && (
          <div
            aria-hidden
            style={{ background: "radial-gradient(120% 100% at 50% 40%, #991b1b 0%, #7f1d1d 55%, #450a0a 100%)" }}
            className="pointer-events-none absolute inset-0 -z-10 animate-hud-pulse motion-reduce:hidden"
          />
        )
      }
      overlay={
        <>
          {confirmDriver && props.onVehicle && (
            <ConfirmDialog
              title="Đổi tài xế?"
              text="Khi xe đang dừng, người lái mới nhìn vào camera khoảng 10 giây."
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
              className="dg-card fixed inset-x-4 bottom-28 z-50 mx-auto w-fit animate-hud-in-fast px-6 py-4 text-hud-body text-hud-ink shadow-2xl"
            >
              {toast}
            </div>
          )}
        </>
      }
    >
      <TopBar {...props} danger={danger} className={`transition-opacity duration-700 ${dim}`} />

      {soundBlocked && (
        <div className="px-4 pb-3.5 hud-sm:px-8">
          <button
            type="button"
            role="alert"
            onClick={props.onEnableSound}
            className="flex min-h-[62px] w-full items-center justify-center gap-3.5 rounded-hud-sm border-0 bg-[linear-gradient(180deg,#fcd34d_0%,#f59e0b_100%)] px-4 text-[19px] font-semibold text-hud-on-warning"
          >
            <VolumeX aria-hidden className="size-6 shrink-0" />
            {SOUND_BLOCKED_TEXT}
          </button>
        </div>
      )}

      {presence ? (
        <PresencePanel unanswered={presence === "unanswered"} remainingS={snap?.presence?.remaining_s ?? null} onAnswer={props.onVehicle} />
      ) : system || !snap ? (
        snap && (system === "unavailable" || system === "camera_lost" || system === "error") ? (
          <main className="grid min-h-0 gap-3.5 px-4 hud-sm:px-8 hud-lg:grid-cols-[minmax(0,1fr)_360px] hud-lg:grid-rows-[minmax(0,1fr)] hud-tall:grid-rows-[minmax(0,1fr)_auto]">
            <IncidentPanel state={system} snap={snap} now={now} />
            <SpeedCard snap={snap} tall={false} />
          </main>
        ) : (
          <main className="grid min-h-0 px-4 hud-sm:px-8">
            <IncidentPanel state={system ?? "connecting"} snap={snap} now={now} edgeUrl={edgeUrl} />
          </main>
        )
      ) : danger ? (
        <DangerStage reasons={snap.reasons} />
      ) : enrolling && snap.enrollment ? (
        <main className="grid min-h-0 px-4 hud-sm:px-8">
          <EnrollPanel enrollment={snap.enrollment} camera={props.camera ?? null} />
        </main>
      ) : (
        <main
          className={`grid min-h-0 gap-3.5 px-4 transition-opacity duration-700 hud-sm:px-8 hud-lg:grid-cols-[minmax(0,1fr)_360px] ${
            dashboard
              ? "hud-lg:grid-rows-[minmax(0,1fr)_220px] hud-tall:grid-rows-[minmax(0,1fr)_auto_auto]"
              : "hud-lg:grid-rows-[minmax(0,1fr)] hud-tall:grid-rows-[minmax(0,1fr)_auto]"
          } ${dim}`}
        >
          {consent ? (
            <ConsentPanel onAnswer={props.onVehicle} />
          ) : level === 2 ? (
            <WarningStage snap={snap} rising={rising} />
          ) : (
            <>
              <StatusCard snap={snap} level={level} rising={rising} />
              <MetricsCard snap={snap} level={level} />
            </>
          )}
          <SpeedCard snap={snap} tall={dashboard} />
        </main>
      )}

      <BottomBar
        snap={snap}
        level={level}
        system={system}
        now={now}
        target={danger || enrolling ? null : feedbackTarget}
        onFalseAlarm={onFalseAlarm}
        // 13/10: also while enrolling (the user's choice); never at L3 (danger)
        onAskDriver={props.onVehicle && !danger ? () => setConfirmDriver(true) : undefined}
        onAskEnd={props.onEndTrip && !danger ? () => setConfirmEnd(true) : undefined}
        note={enrolling && snap?.enrollment ? enrollNote(snap.enrollment) : consent ? "Hướng dẫn sẽ được đọc to bằng giọng nói" : null}
        ending={!!props.ending}
        className={`transition-opacity duration-700 ${dim}`}
      />
    </HudStage>
  );
}

// ------------------------------------------------------------------ top bar

function TopBar({
  snap,
  demo,
  sound,
  cameraLost,
  danger,
  className,
  onEnableSound,
  onToggleDemo,
}: HudViewProps & { danger: boolean; className: string }) {
  return (
    <header className={`relative flex min-w-0 items-center gap-4 px-4 hud-sm:px-8 ${className}`}>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="hud-brand text-[17px] font-semibold tracking-[0.12em]">DRIVERGUARD</span>
        <span className={`hidden text-xs hud-sm:block ${danger ? "text-white/70" : "text-hud-ink-3"}`}>Giám sát tài xế trên thiết bị</span>
      </span>
      <span className="flex-1" />

      {danger ? (
        <AlarmNote sound={sound} />
      ) : (
        <div className="flex min-w-0 items-center gap-2">
          {demo && <span className="dg-chip" style={{ ["--dot" as string]: "var(--series-1)" }}><i />Mô phỏng</span>}
          {/* M28: too slow for a while, alerts may come late. */}
          {snap?.low_fps && snap.connected && (
            <span role="status" className={TOP_NOTE}>
              <Hourglass aria-hidden className="size-4" />
              <span className="hidden hud-md:inline">{LOW_FPS_TEXT}</span>
            </span>
          )}
          {/* M50: the phone detector gives no fresh results; eyes and head are still watched. */}
          {snap?.phone_unavailable && snap.connected && (
            <span role="status" aria-label={PHONE_UNAVAILABLE_TEXT} className={TOP_NOTE}>
              <PhoneOff aria-hidden className="size-4" />
              <span className="hidden hud-md:inline">{PHONE_UNAVAILABLE_TEXT}</span>
            </span>
          )}
          {cameraLost ? (
            <span role="img" aria-label="Mất camera" className={`${TOP_TILE} inline-grid !text-hud-caution`}>
              <CameraOff aria-hidden className="size-[18px]" />
            </span>
          ) : (
            <span role="img" aria-label="Camera hoạt động" className={`${TOP_TILE} hidden hud-sm:inline-grid`}>
              <Camera aria-hidden className="size-[18px]" />
            </span>
          )}
          {/* Sound is always on (no mute: alerts must be heard). Amber while the browser blocks it. */}
          {sound ? (
            <span role="img" aria-label="Âm thanh cảnh báo đang bật" className={`${TOP_TILE} inline-grid`}>
              <Volume2 aria-hidden className="size-[18px]" />
            </span>
          ) : (
            <button type="button" aria-label="Bật âm thanh cảnh báo" onClick={onEnableSound} className={`${TOP_TILE} inline-grid cursor-pointer !text-hud-caution`}>
              <VolumeX aria-hidden className="size-[18px]" />
            </button>
          )}
          {/* M72: both take the screen (and the alert sounds) away, so not while a driver is watched. */}
          {onToggleDemo && (
            <>
              <button
                type="button"
                aria-label={demo ? "Về thiết bị thật" : "Chạy mô phỏng"}
                title={demo ? "Về thiết bị thật" : "Chạy mô phỏng"}
                onClick={onToggleDemo}
                className={`${TOP_TILE} hidden cursor-pointer hud-sm:inline-grid`}
              >
                {demo ? <Square aria-hidden className="size-[18px]" /> : <Play aria-hidden className="size-[18px]" />}
              </button>
              <a href="#/dashboard" aria-label="Dashboard" title="Dashboard" className={`${TOP_TILE} hidden hud-sm:inline-grid`}>
                <LayoutDashboard aria-hidden className="size-[18px]" />
              </a>
            </>
          )}
          <span className="dg-tile inline-flex h-10 items-center gap-2.5 px-3.5">
            {snap?.dim ? <Moon aria-label="Ban đêm" className="size-4 text-[#bdbdbd]" /> : <Clock aria-hidden className="size-4 text-[#bdbdbd]" />}
            <span className="dg-num text-[17px] font-medium">{clockText(snap?.clock_hour)}</span>
          </span>
        </div>
      )}
    </header>
  );
}

function AlarmNote({ sound }: { sound: boolean }) {
  // L3: the only thing on the top bar is that the alarm is sounding (the amber strip says it is not).
  if (!sound) return null;
  return (
    <span className="inline-flex h-10 items-center gap-2.5 rounded-[8px] border border-solid border-white/20 bg-black/25 px-3.5 text-sm font-medium">
      <Volume2 aria-hidden className="size-[18px]" />
      Còi đang kêu
    </span>
  );
}

// ------------------------------------------------------------------ L0 / L1: status card
// Review 07/10: no card title, the green dot alone says "monitored"; a big filled level badge, big words,
// two big tiles with few words (the driver glances, does not read).

const TONE_TEXT: Record<Tone, string> = { ok: "text-hud-safe", caution: "text-hud-caution", danger: "text-[#f87171]" };
const TONE_FILL: Record<Tone, string> = { ok: "var(--good)", caution: "var(--warning)", danger: "#f87171" };

function StatusCard({ snap, level, rising }: { snap: HudSnapshot; level: Level; rising: boolean }) {
  const ordered = orderedReasons(snap.reasons);
  const primary = level > 0 ? (ordered[0] ?? null) : null;
  const ReasonIcon = (primary && REASON_ICONS[primary]) || CircleAlert;
  const headline = primary ? REASON_ACTIONS[primary] : level === 0 ? "Tỉnh táo" : LEVELS[level].title;
  const sub = level === 0 ? "Tiếp tục lái an toàn" : ordered.map(reasonText).join(" · ");
  const long = headline.split(" ").length > 3;
  const last = snap.alerts[0];

  return (
    <section
      aria-live={level ? "assertive" : "polite"}
      aria-atomic="true"
      className={`dg-alert ${level === 1 ? "l1" : "l0"} relative flex min-h-[46dvh] flex-col justify-between gap-6 px-7 py-7 hud-lg:col-start-1 hud-lg:row-start-1 hud-lg:min-h-0 hud-tall:min-h-0`}
    >
      {level === 1 ? (
        <span className="absolute top-6 right-6 inline-flex items-center gap-2 rounded-hud-xs bg-hud-caution px-3 py-1.5 text-base font-semibold text-hud-on-warning">
          <CircleAlert aria-hidden className="size-5" strokeWidth={2.5} />
          {LEVELS[1].title}
        </span>
      ) : (
        <span role="img" aria-label="Đang theo dõi" className="absolute top-7 right-7 size-4 rounded-full bg-hud-safe shadow-[0_0_0_6px_rgba(74,222,128,0.18)]" />
      )}

      {/* Re-mounted on every level / reason change, so the enter animation plays once per alert. */}
      <div
        key={`${level}:${primary ?? ""}`}
        className={`flex flex-1 items-center gap-8 motion-reduce:animate-none ${rising ? "animate-hud-in-fast" : "animate-hud-in-slow"}`}
      >
        {/* Level badge: a filled circle (L0 tick, L1 the reason), shape + colour + words. */}
        <div
          aria-hidden
          className={`grid size-24 shrink-0 place-items-center rounded-full hud-sm:size-[124px] ${
            level === 1 ? "bg-hud-caution text-hud-on-warning" : "bg-hud-safe text-[#05210f]"
          } shadow-[0_10px_40px_rgba(0,0,0,0.35)]`}
        >
          {level === 1 ? <ReasonIcon className="size-14 hud-sm:size-16" strokeWidth={2.25} /> : <Check className="size-14 hud-sm:size-[72px]" strokeWidth={3} />}
        </div>
        <div className="min-w-0">
          <h1
            className={`m-0 leading-[1.02] font-semibold tracking-[-0.035em] text-balance ${
              long ? "text-[clamp(40px,5.6cqw,72px)] hud-tall:text-[54px]" : "text-[clamp(52px,7.5cqw,96px)] hud-tall:text-[68px]"
            }`}
          >
            {headline}
          </h1>
          <p className={`m-0 mt-3 text-[clamp(20px,2.2cqw,28px)] font-medium ${level === 1 ? "text-[#f3dfae]" : "text-[#c6e6cf]"}`}>{sub}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 hud-sm:grid-cols-2">
        {snap.trip && <BigTile icon={Clock} value={durationText(snap.trip.drive_run_s)} label="Lái liên tục" />}
        <BigTile
          icon={History}
          value={last ? `${hourMinute(last.at)} · ${REASON_SHORT[orderedReasons(last.reasons)[0]] ?? LEVELS[last.level].title}` : "Chưa có"}
          label="Cảnh báo gần nhất"
        />
      </div>
    </section>
  );
}

function BigTile({ icon: Icon, value, label }: { icon: LucideIcon; value: string; label: string }) {
  return (
    <div className="dg-tile flex min-w-0 items-center gap-4 px-4 py-3.5">
      <Icon aria-hidden className="size-8 shrink-0 text-[#d4d4d4]" strokeWidth={1.75} />
      <span className="flex min-w-0 flex-col">
        <span className="dg-num truncate text-[28px] leading-tight font-semibold">{value}</span>
        <span className="text-base text-hud-ink-2">{label}</span>
      </span>
    </div>
  );
}

// ------------------------------------------------------------------ L0 / L1: the driver now, in words + the last minutes
// Review 07/10: "52/100" means nothing to a driver; each measure is a word in its colour (the number stays
// small for the curious). The fatigue chart is a slim strip of the last minutes, with times under it.

function MetricsCard({ snap, level }: { snap: HudSnapshot; level: Level }) {
  const trip = snap.trip;
  const l1 = trip?.score_l1 ?? HUD_DEFAULTS.score_l1;
  const l2 = trip?.score_l2 ?? HUD_DEFAULTS.score_l2;
  const drowsy = drowsyWord(snap.drowsy_score, l1, l2);
  const attention = attentionWord(level > 0 ? snap.reasons : [], level);
  const eyes = eyesWord(snap.eyes_closed_s, (v) => formatNumber(v, 1), snap.display ?? HUD_DEFAULTS);
  const slots = trendSlots(trip);

  return (
    <section aria-label="Chỉ số tài xế" className="dg-card flex flex-col justify-center gap-4 px-6 py-5 hud-lg:col-start-1 hud-lg:row-start-2">
      <div className="grid grid-cols-1 gap-3 hud-sm:grid-cols-3">
        <WordTile icon={Coffee} label="Buồn ngủ" {...drowsy} value={snap.drowsy_score} />
        <WordTile icon={Navigation} label="Nhìn đường" {...attention} value={snap.distraction_score} />
        <WordTile icon={eyes.tone === "ok" ? Eye : EyeOff} label="Mắt" {...eyes} />
      </div>
      {slots.length > 0 && trip && <FatigueStrip slots={slots} window={trip.window_min ?? slots.length} />}
    </section>
  );
}

function WordTile({ icon: Icon, label, word, tone, value }: { icon: LucideIcon; label: string; word: string; tone: Tone; value?: number }) {
  return (
    <div className="dg-tile flex min-w-0 items-center gap-3.5 px-4 py-3">
      <Icon aria-hidden className={`size-7 shrink-0 ${TONE_TEXT[tone]}`} strokeWidth={1.75} />
      <span className="flex min-w-0 flex-1 flex-col gap-1">
        <span className="text-[15px] text-hud-ink-2">{label}</span>
        <span className={`truncate text-[24px] leading-tight font-semibold ${TONE_TEXT[tone]}`}>{word}</span>
        {value != null && (
          <span role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(value)} className="dg-meter !h-1">
            <b style={{ width: `${Math.max(0, Math.min(100, value))}%`, ["--fill" as string]: TONE_FILL[tone] }} />
          </span>
        )}
      </span>
    </div>
  );
}

/** The last minutes' fatigue as a slim strip: one cell per minute, coloured by band, times underneath. */
function FatigueStrip({ slots, window }: { slots: TrendSlot[]; window: number }) {
  const marks = [window, Math.round((window * 2) / 3), Math.round(window / 3)];
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-[15px] text-hud-ink-2">Độ mệt từng phút</span>
      <div role="img" aria-label={`Độ mệt từng phút trong ${window} phút gần đây`} className="flex h-5 gap-1">
        {slots.map((s, i) => (
          <div
            key={i}
            className="flex-1 rounded-[3px]"
            style={{
              background: s.kind === "score" ? TONE_FILL[s.band === 2 ? "danger" : s.band === 1 ? "caution" : "ok"] : s.kind === "gap" ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.04)",
              opacity: s.kind === "score" && !s.current ? 0.8 : 1,
            }}
          />
        ))}
      </div>
      <div className="dg-num flex justify-between text-[13px] text-hud-ink-3">
        {marks.map((m) => (
          <span key={m}>{m} phút trước</span>
        ))}
        <span>Bây giờ</span>
      </div>
    </div>
  );
}

// ------------------------------------------------------------------ L2: solid orange card, no chart

function WarningStage({ snap, rising }: { snap: HudSnapshot; rising: boolean }) {
  const ordered = orderedReasons(snap.reasons);
  const primary = ordered[0] ?? null;
  const Icon = (primary && REASON_ICONS[primary]) || TriangleAlert;
  const headline = primary ? REASON_ACTIONS[primary] : LEVELS[2].action;
  const alert = snap.alerts.find((a) => a.level === 2);
  const detail = alertDetail(alert, hourMinute, (v) => formatNumber(v, 1));
  const tile = "rounded-hud-sm border border-solid border-hud-on-warning/16 bg-hud-on-warning/12 px-3.5 py-2.5";

  return (
    <section
      aria-live="assertive"
      aria-atomic="true"
      className="dg-alert l2 flex min-h-[52dvh] flex-col justify-between gap-6 px-6 py-6 hud-sm:px-8 hud-lg:col-start-1 hud-lg:row-start-1 hud-lg:min-h-0 hud-tall:min-h-0"
    >
      <span className="inline-flex items-center gap-2 self-end rounded-hud-xs border border-solid border-hud-on-warning/18 bg-hud-on-warning/14 px-3 py-1.5 text-base font-semibold">
        <TriangleAlert aria-hidden className="size-5" strokeWidth={2.5} />
        {LEVELS[2].title}
      </span>

      <div
        key={`2:${primary ?? ""}`}
        className={`flex flex-col gap-6 motion-reduce:animate-none hud-sm:flex-row hud-sm:items-center hud-sm:gap-9 ${rising ? "animate-hud-in-fast" : "animate-hud-in-slow"}`}
      >
        <div className="grid size-28 shrink-0 place-items-center rounded-hud-xl border border-solid border-hud-on-warning/18 bg-hud-on-warning/12 hud-sm:size-[150px]">
          <Icon aria-hidden className="size-16 hud-sm:size-20" strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <h1 className="m-0 text-[clamp(44px,7cqw,92px)] hud-tall:text-[64px] leading-[0.98] font-bold tracking-[-0.035em] text-balance">{headline}</h1>
          <p className="m-0 mt-[18px] text-2xl font-medium opacity-80">{ordered.map(reasonText).join(" · ")}</p>
        </div>
      </div>

      <div className="flex flex-col gap-2.5">
        <div aria-label="Thông số" className="grid grid-cols-1 gap-2.5 hud-sm:grid-cols-3">
          {[
            { label: "Buồn ngủ", ...drowsyWord(snap.drowsy_score, snap.trip?.score_l1 ?? HUD_DEFAULTS.score_l1, snap.trip?.score_l2 ?? HUD_DEFAULTS.score_l2) },
            { label: "Nhìn đường", ...attentionWord(snap.reasons, 2) },
            { label: "Mắt", ...eyesWord(snap.eyes_closed_s, (v) => formatNumber(v, 1), snap.display ?? HUD_DEFAULTS) },
          ].map((m) => (
            <div key={m.label} className={tile}>
              <span className="block text-[15px] opacity-75">{m.label}</span>
              <span className="block text-[22px] leading-tight font-bold">{m.word}</span>
            </div>
          ))}
        </div>
        {detail && <span className="text-base font-medium opacity-75">{detail}</span>}
      </div>
    </section>
  );
}

// ------------------------------------------------------------------ L3: the red screen, nothing else

function DangerStage({ reasons }: { reasons: Reason[] }) {
  const primary = orderedReasons(reasons)[0] ?? null;
  const [order, todo] = splitAction(primary ? REASON_ACTIONS[primary] : LEVELS[3].action);
  return (
    <main aria-live="assertive" aria-atomic="true" className="flex flex-col items-center justify-center gap-7 px-4 text-center hud-sm:px-8">
      <span className="inline-flex items-center gap-2 rounded-[8px] border border-solid border-white/20 bg-black/25 px-4 py-2 text-base font-semibold tracking-[0.04em]">
        NGUY HIỂM
      </span>
      <OctagonAlert aria-hidden className="size-28 drop-shadow-[0_8px_30px_rgba(0,0,0,0.35)] hud-sm:size-[150px]" strokeWidth={1.4} />
      <h1 className="m-0 flex flex-col items-center gap-3 text-[clamp(64px,10cqw,128px)] hud-tall:text-[112px] leading-[0.95] font-bold tracking-[-0.04em]">
        {order}
        {todo && (
          <>
            {" "}
            <span className="text-[clamp(30px,4cqw,52px)] leading-[1.1] font-semibold tracking-[-0.02em]">{todo}</span>
          </>
        )}
      </h1>
    </main>
  );
}

// ------------------------------------------------------------------ vehicle: turn signals, gear, speed
// Review 07/10: no card title; turn signals on top; the gear is one big letter (D driving, P parked in
// blue); a green tick alone says the vehicle signal is fine, a chip only when it is not.

function SpeedCard({ snap, tall }: { snap: HudSnapshot; tall: boolean }) {
  const v = snap.vehicle;
  const speed = v ? v.speed_kmh : (snap.speed_kmh ?? 0); // null: link lost while driving, speed unknown
  const driving = isDriving(snap);
  const turn = v?.turn_signal ?? null;
  const lost = v?.signal_lost === true;
  const noSignal = v?.source === "sim" && !v.connected && !lost;
  const enrolling = ["look_camera", "look_road", "close_eyes"].includes(snap.enrollment?.status ?? "");

  return (
    <section
      aria-label="Xe"
      className={`dg-card relative flex min-h-0 flex-col gap-4 px-5 pt-5 pb-5 hud-lg:col-start-2 hud-lg:row-start-1 ${tall ? "hud-lg:row-span-2" : ""}`}
    >
      <div className="grid grid-cols-3 gap-3">
        <TurnTile side="left" on={turn === "left"} />
        <div
          className={`grid h-[84px] place-items-center rounded-hud-sm ${driving ? "dg-tile" : "bg-hud-system text-[#0b1b33]"}`}
          title={driving ? "Đang lái" : "Đang đỗ"}
        >
          <span aria-hidden className="hud-gear text-[44px] leading-none font-bold">{driving ? "D" : "P"}</span>
          {/* The words for screen readers (and the e2e test); the letter says it on screen. */}
          <span className="sr-only">{driving ? "Đang lái" : enrolling ? "Xe đang đỗ · đang làm quen khuôn mặt" : "Đang đỗ"}</span>
        </div>
        <TurnTile side="right" on={turn === "right"} />
      </div>

      {lost || noSignal ? (
        <span className="dg-chip w-fit self-center !text-[15px]" style={{ ["--dot" as string]: lost ? "var(--warning)" : "var(--series-1)" }}>
          <i />
          {lost
            ? v?.never_received
              ? "Chưa có tín hiệu tốc độ · theo dõi như đang chạy"
              : driving
                ? "Mất tín hiệu tốc độ · vẫn theo dõi"
                : "Mất tín hiệu tốc độ · coi như đỗ"
            : "Chưa có tín hiệu tốc độ · coi như đỗ"}
        </span>
      ) : (
        <span role="img" aria-label="Tín hiệu xe đã kết nối" className="absolute right-5 bottom-5 grid size-9 place-items-center rounded-full bg-hud-safe/15 text-hud-safe">
          <Check aria-hidden className="size-5" strokeWidth={3} />
        </span>
      )}

      <div className="grid min-h-0 flex-1 place-items-center">
        <div
          role="img"
          aria-label={speed == null ? "Tốc độ không rõ" : `Tốc độ ${Math.round(speed)} km/h`}
          className="relative aspect-[320/280] h-full max-h-[300px] max-w-full min-h-[180px] [container-type:size]"
        >
          <svg aria-hidden viewBox="0 0 320 280" className="block size-full overflow-visible">
            <defs>
              <linearGradient id="hud-oct-glass" gradientUnits="userSpaceOnUse" x1="0" y1="20" x2="0" y2="252">
                <stop offset="0%" stopColor="#fff" stopOpacity="0" />
                <stop offset="35%" stopColor="#fff" stopOpacity="0.035" />
                <stop offset="70%" stopColor="#fff" stopOpacity="0.075" />
                <stop offset="100%" stopColor="#fff" stopOpacity="0.12" />
              </linearGradient>
              <linearGradient id="hud-oct-rim" gradientUnits="userSpaceOnUse" x1="0" y1="20" x2="0" y2="252">
                <stop offset="0%" stopColor="#fff" stopOpacity="0.05" />
                <stop offset="100%" stopColor="#fff" stopOpacity="0.32" />
              </linearGradient>
            </defs>
            <polyline points="97,24 43,102 43,176 102,239 218,239 277,176 277,102 223,24" fill="none" stroke="url(#hud-oct-glass)" strokeWidth="26" strokeLinejoin="miter" />
            <polyline points="86,20 30,100 30,180 96,252 224,252 290,180 290,100 234,20" fill="none" stroke="url(#hud-oct-rim)" strokeWidth="1.4" strokeLinejoin="round" />
            <polyline points="108,28 56,104 56,172 108,226 212,226 264,172 264,104 212,28" fill="none" stroke="url(#hud-oct-rim)" strokeWidth="1" strokeLinejoin="round" opacity="0.6" />
          </svg>
          <div className="absolute inset-x-0 top-[24%] flex flex-col items-center gap-1.5">
            <span className="dg-num text-[36cqh] leading-[0.95] font-semibold tracking-[-0.03em]">{speed == null ? "– –" : Math.round(speed)}</span>
            <span className="text-lg text-hud-ink-2">km/h</span>
          </div>
        </div>
      </div>
    </section>
  );
}

// Turn signal: amber arrow blinking like the car's own indicator (static with reduced motion).
function TurnTile({ side, on }: { side: "left" | "right"; on: boolean }) {
  const Icon = side === "left" ? ArrowBigLeft : ArrowBigRight;
  return (
    <div
      role="img"
      aria-label={`Xi nhan ${side === "left" ? "trái" : "phải"}: ${on ? "đang bật" : "tắt"}`}
      className={`grid h-[84px] place-items-center rounded-hud-sm ${on ? "border border-solid border-hud-turn/50 bg-hud-turn/15" : "dg-tile"}`}
    >
      <Icon
        aria-hidden
        className={`size-12 ${on ? "fill-hud-turn text-hud-turn animate-hud-blink motion-reduce:animate-none" : "text-hud-ink-3 opacity-60"}`}
      />
    </div>
  );
}

// ------------------------------------------------------------------ not monitored (design "Tạm ngưng", "Mất camera", "Lỗi xử lý",
// "Mất kết nối"): an amber card that says the driver is NOT watched, why, and what happens next.
// Review 07/10: "no face" and "camera broken" must never look alike: the first line says whether the
// camera still works, the camera tile is green (works) or red (no picture), and the icons differ.

function IncidentPanel({ state, snap, now, edgeUrl }: { state: SystemState; snap: HudSnapshot | null; now: number; edgeUrl?: string }) {
  const cause = snap?.unavailable_reason ?? null;
  const incident = snap?.incident ?? null;
  const since = incident?.since != null ? `Từ ${hourMinute(incident.since)}` : null;
  const reported =
    incident?.reported === true ? { value: "Đã báo", label: "Cho quản lý đội xe" } : incident?.reported === false ? { value: "Đang báo…", label: "Cho quản lý đội xe" } : null;

  let view: { Icon: LucideIcon; title: string; lead: string; tiles: { icon: LucideIcon; value: string; label: string; tone?: Tone }[]; note: string };
  if (state === "unavailable") {
    const text = cause ? UNAVAILABLE_CAUSES[cause] : UNAVAILABLE_CAUSES.no_face;
    view = {
      Icon: ScanFace,
      title: SYSTEM_TEXT.unavailable.title,
      lead: `Camera vẫn chạy, nhưng ${text.short}`,
      tiles: [
        { icon: Camera, value: "Vẫn hoạt động", label: "Camera", tone: "ok" as const },
        { icon: History, value: "Tự động", label: cause === "slow_loop" ? "Theo dõi lại khi máy xử lý kịp" : "Theo dõi lại khi thấy rõ mặt" },
      ],
      note: `${text.detail} Lần này không tính là cảnh báo.`,
    };
  } else if (state === "camera_lost") {
    view = {
      Icon: CameraOff,
      title: SYSTEM_TEXT.camera_lost.title,
      lead: "Không nhận được hình từ camera",
      tiles: [
        { icon: CameraOff, value: "Không có hình", label: "Camera", tone: "danger" as const },
        incident?.attempts != null
          ? { icon: LoaderCircle, value: `Lần thử ${incident.attempts}`, label: "Đang kết nối lại…" }
          : { icon: LoaderCircle, value: "Đang kết nối lại…", label: "Tự động" },
        ...(since ? [{ icon: Clock, value: since, label: "Thời điểm mất camera" }] : []),
        ...(reported ? [{ icon: Send, ...reported }] : []),
      ].slice(0, 3),
      note: "Lỗi kéo dài: khi dừng xe, kiểm tra dây và ống kính camera.",
    };
  } else if (state === "error") {
    view = {
      Icon: CircleAlert,
      title: SYSTEM_TEXT.error.title,
      lead: "Camera có hình, nhưng máy không xử lý được",
      tiles: [
        { icon: LoaderCircle, value: "Đang thử lại…", label: "Tự động" },
        ...(since ? [{ icon: Clock, value: since, label: "Thời điểm lỗi" }] : []),
        ...(reported ? [{ icon: Send, ...reported }] : []),
      ],
      note: "Lỗi kéo dài: tìm chỗ dừng xe an toàn.",
    };
  } else {
    // down / stale / connecting: the screen hears nothing from the device.
    const last = snap?.updated_at;
    view = {
      Icon: state === "connecting" ? LoaderCircle : WifiOff,
      title: SYSTEM_TEXT[state].title,
      lead: state === "connecting" ? SYSTEM_TEXT.connecting.detail : "Màn hình chưa nhận được tín hiệu từ thiết bị",
      tiles: [
        { icon: LoaderCircle, value: "Đang thử lại", label: "Tự động" },
        ...(last ? [{ icon: Clock, value: `${hourMinute(last)} · ${Math.max(0, Math.round(now - last))} giây trước`, label: "Lần cuối nhận dữ liệu" }] : []),
        { icon: Cable, value: "Nguồn và cáp", label: "Kiểm tra khi dừng xe" },
      ],
      note: `Tốc độ và trạng thái của bạn sẽ hiện lại ngay khi có kết nối.${import.meta.env.DEV && edgeUrl ? ` Màn hình đọc thiết bị tại ${edgeUrl}; chạy python -m edge_agent.main --source 0 hoặc bấm "Chạy mô phỏng".` : ""}`,
    };
  }
  const deviceSide = state === "down" || state === "stale" || state === "connecting";

  return (
    <section aria-live="assertive" className={`dg-alert ${deviceSide ? "sys" : "l1"} relative flex min-h-[46dvh] flex-col justify-between gap-6 px-7 py-7 hud-lg:min-h-0 hud-tall:min-h-0`}>
      <span className="dg-chip solid-warn absolute top-6 right-6 !px-3 !py-1.5 !text-base">
        <EyeOff aria-hidden className="size-5" strokeWidth={2.25} />
        Chưa theo dõi
      </span>
      <div className="flex flex-1 items-center gap-8">
        <div className={`grid size-24 shrink-0 place-items-center rounded-full hud-sm:size-[124px] ${deviceSide ? "bg-hud-system/20 text-[#93c5fd]" : "bg-hud-caution/18 text-hud-caution"}`}>
          <view.Icon aria-hidden className={`size-14 hud-sm:size-16 ${state === "connecting" ? "animate-spin motion-reduce:animate-none" : ""}`} strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <h1 className="m-0 text-[clamp(44px,6.2cqw,80px)] hud-tall:text-[60px] leading-[1.02] font-semibold tracking-[-0.035em] text-balance">{view.title}</h1>
          <p className={`m-0 mt-3 text-[clamp(20px,2.4cqw,30px)] font-medium ${deviceSide ? "text-[#bfd8fb]" : "text-[#fcd34d]"}`}>{view.lead}</p>
        </div>
      </div>
      <div className="flex flex-col gap-3">
        <div className={`grid grid-cols-1 gap-3 ${view.tiles.length >= 3 ? "hud-sm:grid-cols-3 hud-tall:grid-cols-1" : "hud-sm:grid-cols-2"}`}>
          {view.tiles.map((t) => (
            <IncidentTile key={t.label + t.value} {...t} />
          ))}
        </div>
        <span className="text-[17px] text-hud-ink-2">{view.note}</span>
      </div>
    </section>
  );
}

function IncidentTile({ icon: Icon, value, label, tone }: { icon: LucideIcon; value: string; label: string; tone?: Tone }) {
  return (
    <div className="dg-tile flex min-w-0 items-center gap-4 px-4 py-3.5">
      <Icon aria-hidden className={`size-8 shrink-0 ${tone ? TONE_TEXT[tone] : "text-[#d4d4d4]"}`} strokeWidth={1.75} />
      <span className="flex min-w-0 flex-col">
        <span className={`truncate text-[24px] leading-tight font-semibold ${tone ? TONE_TEXT[tone] : ""}`}>{value}</span>
        <span className="text-base text-hud-ink-2">{label}</span>
      </span>
    </div>
  );
}

// ------------------------------------------------------------------ bottom bar

function BottomBar({
  snap,
  level,
  system,
  now,
  target,
  onFalseAlarm,
  onAskDriver,
  onAskEnd,
  note,
  ending,
  className,
}: {
  snap: HudSnapshot | null;
  level: Level;
  system: SystemState | null;
  now: number;
  target: HudAlert | null;
  onFalseAlarm: () => void;
  onAskDriver?: () => void;
  onAskEnd?: () => void;
  note: string | null; // replaces the computed note (enrollment, consent)
  ending: boolean;
  className: string;
}) {
  if (level === 3 && !system) {
    // L3: no button; only how long the eyes have been closed.
    const closed = snap?.eyes_closed_s ?? 0;
    return (
      <footer className="flex justify-center px-4 pb-6 hud-sm:px-8">
        {closed > 0 && (
          <span className="dg-num inline-flex items-center gap-3 rounded-[10px] border border-solid border-white/20 bg-black/28 px-6 py-3.5 text-[26px] font-semibold">
            <EyeOff aria-hidden className="size-[26px]" />
            Mắt nhắm {formatNumber(closed, 1)} giây
          </span>
        )}
      </footer>
    );
  }
  const left = target && snap ? (
    <FalseAlarmButton target={target} level={level} now={now} windowS={snap.feedback_window_s ?? HUD_DEFAULTS.feedback_window_s} onPress={onFalseAlarm} />
  ) : (
    <span className="flex min-w-0 items-center gap-3 text-lg text-hud-ink-2 hud-tall:col-span-2">
      <Flag aria-hidden className="size-[18px] shrink-0" />
      <span className="min-w-0">{note ?? (snap ? noteFor(snap) : "Đang chờ dữ liệu từ thiết bị")}</span>
    </span>
  );
  return (
    <footer className={`grid items-center gap-3.5 px-4 pt-3.5 pb-5 hud-sm:grid-cols-[minmax(0,1fr)_250px_290px] hud-sm:px-8 hud-tall:grid-cols-2 ${className}`}>
      {left}
      {onAskDriver ? (
        <button type="button" onClick={onAskDriver} className="dg-btn dg-btn-lg whitespace-nowrap">
          <span className="flex items-center gap-3">
            <UserRoundCog aria-hidden className="size-7" />
            Đổi tài xế
          </span>
          <ChevronRight aria-hidden className="size-6 text-hud-ink-3" />
        </button>
      ) : (
        <span className="hidden hud-sm:block" />
      )}
      {onAskEnd ? (
        <button type="button" onClick={onAskEnd} disabled={ending} className="dg-btn dg-btn-lg whitespace-nowrap">
          <span className="flex items-center gap-3">
            <FlagTriangleRight aria-hidden className="size-7" />
            {ending ? "Đang kết thúc…" : "Kết thúc ca lái"}
          </span>
          <ChevronRight aria-hidden className="size-6 text-hud-ink-3" />
        </button>
      ) : (
        <span className="hidden hud-sm:block" />
      )}
    </footer>
  );
}

function noteFor(snap: HudSnapshot): string {
  const v = snap.vehicle;
  const last = snap.alerts[0];
  const lastAlert = last
    ? last.feedback
      ? `Đã ghi nhận: cảnh báo lúc ${hourMinute(last.at)} là nhầm`
      : `Cảnh báo gần nhất lúc ${hourMinute(last.at)} · ${reasonText(orderedReasons(last.reasons)[0])}`
    : null;
  return footerNote(snap, {
    signalLost: v?.signal_lost ? VEHICLE_SIGNAL_LOST_TEXT[v.never_received ? "never" : v.driving ? "driving" : "parked"] : null,
    lowFps: "Máy đang chậm · cảnh báo có thể trễ",
    phoneOff: `${PHONE_UNAVAILABLE_TEXT} · mắt và đầu vẫn được theo dõi`,
    enroll: enrollReminder(snap.enrollment),
    lastAlert,
  });
}

function FalseAlarmButton({ target, level, now, windowS, onPress }: { target: HudAlert; level: Level; now: number; windowS: number; onPress: () => void }) {
  const left = Math.max(0, Math.round(target.at + windowS - now));
  const ring = target.level >= 2 || level === 2 ? "ring-hud-warning/80" : "ring-hud-caution/70";
  return (
    <button type="button" onClick={onPress} className={`dg-btn dg-btn-lg justify-self-start !justify-start gap-4 ring-2 hud-tall:col-span-2 hud-tall:justify-self-stretch ${ring}`}>
      <Flag aria-hidden className="size-7 shrink-0" />
      <span className="flex flex-col gap-0.5">
        <span className="text-xl font-semibold">Cảnh báo nhầm?</span>
        <span className="dg-num text-[15px] text-hud-ink-2">
          Chạm để báo · còn {Math.floor(left / 60)}:{String(left % 60).padStart(2, "0")}
        </span>
      </span>
    </button>
  );
}

// ------------------------------------------------------------------ enrollment, dialogs, system screens (restyled in M59)

// Before the enrollment steps (design "Đăng ký · Xin đồng ý"): why the face is enrolled and what happens
// to the data; the steps start on "Đồng ý". A device screen, so it is blue (system), never a level colour.
function ConsentPanel({ onAnswer }: { onAnswer?: (action: VehicleAction) => void }) {
  return (
    <section aria-labelledby="consent-title" className="dg-alert sys flex min-h-0 flex-col gap-5 px-7 py-6">
      <div className="flex items-start justify-between gap-3">
        <span className="dg-card-title">
          <h2 id="consent-title" className="m-0 text-base font-medium">
            {ENROLL_CONSENT.title}
          </h2>
          <span>Khoảng 10 giây · khi xe đang dừng</span>
        </span>
        <span className="dg-chip" style={{ ["--dot" as string]: "var(--series-1)" }}>
          <i />
          Chưa làm quen khuôn mặt
        </span>
      </div>
      <div className="flex items-center gap-6">
        <div className="dg-tile grid size-[88px] shrink-0 place-items-center !rounded-hud-xl text-[#93c5fd]">
          <ScanFace aria-hidden className="size-11" strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <p className="hud-headline m-0 text-[clamp(32px,4cqw,48px)] leading-[1.08] font-semibold tracking-[-0.03em] text-balance">
            {ENROLL_CONSENT.headline}
          </p>
          <p className="m-0 mt-2.5 max-w-[52ch] text-[17px] leading-normal text-[#b8c2d0]">{ENROLL_CONSENT.lead}</p>
        </div>
      </div>
      <ul aria-label="Dữ liệu khuôn mặt của bạn" className="dg-tile m-0 flex list-none flex-col gap-3 px-5 py-[18px]">
        {ENROLL_CONSENT.privacy.map((line) => (
          <li key={line} className="flex gap-3 text-base leading-[1.45] text-[#d4d4d4]">
            <ShieldCheck aria-hidden className="mt-0.5 size-[18px] shrink-0 text-hud-safe" />
            <span>{line}</span>
          </li>
        ))}
      </ul>
      {onAnswer && (
        <div className="mt-auto grid gap-3 hud-sm:grid-cols-[2fr_1fr]">
          <button
            type="button"
            onClick={() => onAnswer("enroll_start")}
            className="h-[60px] cursor-pointer rounded-hud-sm border-0 bg-[linear-gradient(180deg,#3d6aa8_0%,#335c94_100%)] text-lg font-semibold text-white"
          >
            {ENROLL_CONSENT.agree}
          </button>
          <button type="button" onClick={() => onAnswer("enroll_later")} className="dg-btn !h-[60px] !justify-center !text-[17px]">
            {ENROLL_CONSENT.later}
          </button>
        </div>
      )}
      <span className="text-[13px] text-hud-ink-3">{ENROLL_CONSENT.laterNote}</span>
    </section>
  );
}

// Guided enrollment (design "Đăng ký · Bước 1-3/3"): one instruction at a time, big, the step's progress,
// and the face alignment frame. The same words are spoken (HudScreen): steps 2 and 3 are done without
// looking here. No cancel button: driving off pauses the enrollment (edge agent), nothing to cancel.
function EnrollPanel({ enrollment, camera }: { enrollment: HudEnrollment; camera: MediaStream | null }) {
  const voice = useVietnameseVoice();
  const step = enrollStep(enrollment) as EnrollStep;
  const index = ENROLL_STEP_ORDER.indexOf(step);
  const text = ENROLL_STEPS[step];
  const hint = enrollment.hint ? ENROLL_HINTS[enrollment.hint] : null;
  const pct = Math.round(Math.max(0, Math.min(1, enrollment.progress)) * 100);

  return (
    <section
      aria-live="polite"
      aria-atomic="true"
      className="dg-alert sys grid min-h-0 gap-9 px-6 py-6 hud-sm:px-8 hud-lg:grid-cols-[minmax(0,1fr)_380px]"
    >
      <div className="flex min-w-0 flex-col justify-between gap-7">
        <span className="dg-card-title">
          <b>{ENROLL_CONSENT.title}</b>
          <span>Xe đang đỗ · 0 km/h</span>
        </span>
        <div className="flex items-center gap-3.5">
          <ol aria-label="Các bước" className="m-0 flex list-none gap-2 p-0">
            {ENROLL_STEP_ORDER.map((s, i) => (
              <li
                key={s}
                aria-current={i === index ? "step" : undefined}
                className={`h-2 w-12 rounded-full hud-sm:w-[76px] ${i < index ? "bg-hud-safe" : i === index ? "bg-hud-system" : "bg-white/12"}`}
              >
                <span className="sr-only">
                  Bước {i + 1}: {ENROLL_STEPS[s].title}
                </span>
              </li>
            ))}
          </ol>
          <span className="dg-num text-[15px] font-medium text-[#b8c2d0]">
            Bước {index + 1}/{ENROLL_STEP_ORDER.length}
          </span>
        </div>
        {/* Re-mounted per step, so each new instruction animates in once. */}
        <div key={step} className="flex animate-hud-in-fast flex-col gap-3.5 motion-reduce:animate-none">
          <h1 className="m-0 text-[clamp(44px,6cqw,76px)] hud-tall:text-[60px] leading-[1.02] font-semibold tracking-[-0.035em] text-balance">{text.title}</h1>
          <p className="m-0 text-[clamp(20px,2.2cqw,26px)] text-[#b8c2d0]">{text.detail}</p>
        </div>
        <div className="flex flex-col gap-3.5">
          {hint && (
            <span className="inline-flex w-fit items-center gap-2 rounded-hud-xs border border-solid border-hud-caution/40 bg-hud-caution/10 px-2.5 py-1.5 text-[13px] font-medium text-[#fde68a]">
              <span aria-hidden className="size-[7px] rounded-full bg-hud-caution" />
              {hint}
            </span>
          )}
          <div
            role="progressbar"
            aria-label={`Tiến độ bước ${index + 1}`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={pct}
            className="h-2.5 overflow-hidden rounded-full bg-white/8"
          >
            <div
              className="h-full origin-left rounded-full bg-[linear-gradient(90deg,#60a5fa,#93c5fd)] transition-transform duration-300 ease-out"
              style={{ transform: `scaleX(${pct / 100})` }}
            />
          </div>
        </div>
      </div>
      <div className="flex min-h-0 flex-col gap-3">
        <FaceGuide step={step} hint={hint} stream={camera} />
        <span className="flex items-center gap-2.5 text-sm leading-[1.45] text-[#b8c2d0]">
          <Volume2 aria-hidden className="size-[18px] shrink-0 text-[#93c5fd]" />
          {voice === false ? NO_VIETNAMESE_VOICE_TEXT : "Đặt mặt vào khung oval. Hướng dẫn được đọc to, hết bước có tiếng bíp."}
        </span>
      </div>
    </section>
  );
}

function enrollNote(e: HudEnrollment): string {
  const i = Math.max(0, ENROLL_STEP_ORDER.indexOf(enrollStep(e) as EnrollStep));
  const first = e.attempts > 0 ? `Làm lại ${e.attempts} lần` : i === 0 ? "Bước đầu tiên" : i === ENROLL_STEP_ORDER.length - 1 ? "Bước cuối" : `Bước ${i + 1}`;
  return `${first} · tạm dừng nếu xe lăn bánh`;
}

function EndTripDialog({ ending, onCancel, onConfirm }: { ending: boolean; onCancel: () => void; onConfirm: () => void }) {
  return (
    <ConfirmDialog
      title="Kết thúc ca lái?"
      text="Hệ thống ngừng theo dõi, hiện bản tổng kết ca lái và gửi cho quản lý đội xe."
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
          <button type="button" onClick={onCancel} className="min-h-14 rounded-hud-sm border-0 bg-hud-raised text-hud-body font-semibold text-hud-ink ring-1 ring-hud-line">
            {cancel}
          </button>
          <button type="button" onClick={onConfirm} disabled={busy} className="min-h-14 rounded-hud-sm border-0 bg-[linear-gradient(180deg,#3d6aa8_0%,#335c94_100%)] text-hud-body font-semibold text-white disabled:opacity-50">
            {confirm}
          </button>
        </div>
      </div>
    </div>
  );
}

/** "Bạn còn ở đó không?" (M44): the whole panel is one button, hit without aiming. Asked only while the
 *  camera cannot see the driver, so it never takes the eyes off the road of a driver who is watched. */
function PresencePanel({
  unanswered,
  remainingS,
  onAnswer,
}: {
  unanswered: boolean;
  remainingS: number | null;
  onAnswer?: (action: VehicleAction) => void;
}) {
  // M59: the whole card is one 72 px+ target; amber while asking (the driver must act), red once nobody
  // answered (the manager was told). Big words, a countdown, no other button on the screen.
  return (
    <main className="grid min-h-0 px-4 hud-sm:px-8">
      <button
        type="button"
        role="alert"
        onClick={() => onAnswer?.("presence_ok")}
        className={`dg-alert ${unanswered ? "l3t" : "l1"} grid w-full cursor-pointer place-items-center px-8 py-8 text-center font-hud text-hud-ink`}
      >
        <span className="flex flex-col items-center gap-6">
          <span
            aria-hidden
            className={`grid size-28 place-items-center rounded-full shadow-[0_10px_40px_rgba(0,0,0,0.35)] hud-sm:size-[140px] ${
              unanswered ? "bg-[#f87171] text-[#2a0606]" : "bg-hud-caution text-hud-on-warning"
            }`}
          >
            <Hand className="size-16 hud-sm:size-20" strokeWidth={2} />
          </span>
          <span className="block text-[clamp(44px,7cqw,92px)] hud-tall:text-[64px] leading-[1.02] font-semibold tracking-[-0.035em] text-balance">
            {PRESENCE_TEXT.title}
          </span>
          <span className="block text-[clamp(26px,3.4cqw,40px)] font-semibold">{PRESENCE_TEXT.tap}</span>
          <span className={`block text-[clamp(18px,2cqw,24px)] ${unanswered ? "text-[#f3c4c4]" : "text-[#f3dfae]"}`}>
            {unanswered ? PRESENCE_TEXT.unanswered : PRESENCE_TEXT.detail}
          </span>
          {!unanswered && remainingS != null && remainingS > 0 && (
            <span className="dg-num rounded-hud-xs bg-black/25 px-4 py-2 text-xl font-semibold">Còn {Math.ceil(remainingS)} giây</span>
          )}
        </span>
      </button>
    </main>
  );
}
