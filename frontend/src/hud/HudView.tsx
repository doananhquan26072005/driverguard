// In-car HUD view (block 13): presentation only, every value comes in as props
// (HudScreen polls the edge agent, HudPreview feeds fixed scenarios). Version 4 redesign (M58), on
// the DriverGuard design system (dark ground, glass cards lit from the top left, Inter):
// - one glance (< 0.5 s): level colour + level shape + one action sentence
// - the higher the level, the less on screen: L0 has the fatigue chart, L2 drops it, L3 is only the
//   stop order on a red screen (no card, no button)
// - colour is never the only cue: circle with a tick (L0), circle "!" (L1), triangle (L2), octagon (L3)
// - alerts appear in 150 ms, calm-down fades over 600 ms; L3 pulses at 1 Hz
// - at night L0-L1 are dimmed (no glare), L2-L3 always at full brightness
// - no L0-L3 codes for the driver (codes stay on the dashboard)
// - the trip numbers (continuous driving, the last minutes' fatigue, an alert's detail) come from the
//   agent (M65), so a reload shows them again at once; nothing here counts them
// - "Kết thúc chuyến" and "Đổi tài xế" ask once more (no accidental tap while driving)
// - sound is always on; while the browser still blocks it, an amber strip under the top bar asks for
//   one touch (on every screen, also L3 and the system screens)
// Enrollment, consent, presence and system screens keep their M57 look inside this frame until M59.
import { useState } from "react";
import {
  Activity,
  ArrowBigLeft,
  ArrowBigRight,
  Camera,
  CameraOff,
  Car,
  ChevronRight,
  CircleAlert,
  CircleCheck,
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
  Moon,
  OctagonAlert,
  PhoneOff,
  Play,
  ScanFace,
  ShieldCheck,
  Smartphone,
  Square,
  TrendingUp,
  TriangleAlert,
  UserCheck,
  UserRoundCog,
  Volume2,
  VolumeX,
  WifiOff,
  type LucideIcon,
} from "lucide-react";
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
import type { EnrollStep, HudAlert, HudEnrollment, HudSnapshot, Level, Reason, UnavailableCause, VehicleAction } from "../lib/types";
import FaceGuide from "./FaceGuide";
import HudStage from "./HudStage";
import {
  ENROLL_STEP_ORDER,
  alertDetail,
  enrollReminder,
  enrollStep,
  fatigueBand,
  fatigueSummary,
  footerNote,
  isDistractionReason,
  orderedReasons,
  presenceUp,
  showConsentPanel,
  showEnrollPanel,
  splitAction,
  systemState,
  trendSlots,
  type FatigueBand,
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

const SYSTEM_ICONS: Record<SystemState, LucideIcon> = {
  down: WifiOff,
  camera_lost: CameraOff,
  error: CircleAlert,
  unavailable: ScanFace,
  stale: Hourglass,
  connecting: LoaderCircle,
};

// Fatigue bands (fatigueBand): bars and meter fills. Full class strings: Tailwind only generates what it finds.
const BAND_BG: Record<FatigueBand, string> = { 0: "bg-hud-safe", 1: "bg-hud-caution", 2: "bg-[#f87171]" };
const BAND_DOT: Record<FatigueBand, string> = { 0: "var(--good)", 1: "var(--warning)", 2: "#f87171" };

// Small glass square of the top bar (camera, sound, demo, dashboard): 40 px, icon only.
// No display here: each use says inline-grid or hidden sm:inline-grid (two display classes would clash).
const TOP_TILE = "dg-tile size-10 shrink-0 place-items-center text-[#bdbdbd] no-underline";
// Amber outlined note of the top bar (slow machine, phone detector down).
const TOP_NOTE =
  "inline-flex h-10 items-center gap-2 rounded-[10px] border border-solid border-hud-caution/45 bg-hud-caution/12 px-3.5 text-sm font-medium whitespace-nowrap text-[#fcd34d]";

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
  const dim = !system && !!snap?.night && level <= 1 ? "opacity-80" : "";
  const [confirmEnd, setConfirmEnd] = useState(false);
  const [confirmDriver, setConfirmDriver] = useState(false);
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
        <div className="px-4 pb-3.5 sm:px-8">
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
        <PresencePanel unanswered={presence === "unanswered"} onAnswer={props.onVehicle} />
      ) : system || !snap ? (
        <SystemPanel state={system ?? "connecting"} edgeUrl={edgeUrl} cause={snap?.unavailable_reason ?? null} />
      ) : danger ? (
        <DangerStage reasons={snap.reasons} />
      ) : enrolling && snap.enrollment ? (
        <main className="grid min-h-0 px-4 sm:px-8">
          <EnrollPanel enrollment={snap.enrollment} />
        </main>
      ) : (
        <main
          className={`grid min-h-0 gap-3.5 px-4 transition-opacity duration-700 sm:px-8 lg:grid-cols-[minmax(0,1fr)_400px] ${
            dashboard ? "lg:grid-rows-[minmax(0,1fr)_210px]" : "lg:grid-rows-[minmax(0,1fr)]"
          } ${dim}`}
        >
          {consent ? (
            <ConsentPanel onAnswer={props.onVehicle} />
          ) : level === 2 ? (
            <WarningStage snap={snap} rising={rising} />
          ) : (
            <>
              <StatusCard snap={snap} level={level} rising={rising} />
              <FatigueCard snap={snap} level={level} />
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
        onAskDriver={props.onVehicle && !danger && !enrolling ? () => setConfirmDriver(true) : undefined}
        onAskEnd={props.onEndTrip && !danger && !enrolling ? () => setConfirmEnd(true) : undefined}
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
    <header className={`relative flex min-w-0 items-center gap-4 px-4 sm:px-8 ${className}`}>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="text-[17px] font-semibold tracking-[0.12em]">DRIVERGUARD</span>
        <span className={`hidden text-xs sm:block ${danger ? "text-white/70" : "text-hud-ink-3"}`}>Giám sát tài xế trên thiết bị</span>
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
              <span className="hidden md:inline">{LOW_FPS_TEXT}</span>
            </span>
          )}
          {/* M50: the phone detector gives no fresh results; eyes and head are still watched. */}
          {snap?.phone_unavailable && snap.connected && (
            <span role="status" aria-label={PHONE_UNAVAILABLE_TEXT} className={TOP_NOTE}>
              <PhoneOff aria-hidden className="size-4" />
              <span className="hidden md:inline">{PHONE_UNAVAILABLE_TEXT}</span>
            </span>
          )}
          {cameraLost ? (
            <span role="img" aria-label="Mất camera" className={`${TOP_TILE} inline-grid !text-hud-caution`}>
              <CameraOff aria-hidden className="size-[18px]" />
            </span>
          ) : (
            <span role="img" aria-label="Camera hoạt động" className={`${TOP_TILE} hidden sm:inline-grid`}>
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
          <button
            type="button"
            aria-label={demo ? "Về thiết bị thật" : "Chạy mô phỏng"}
            title={demo ? "Về thiết bị thật" : "Chạy mô phỏng"}
            onClick={onToggleDemo}
            className={`${TOP_TILE} hidden cursor-pointer sm:inline-grid`}
          >
            {demo ? <Square aria-hidden className="size-[18px]" /> : <Play aria-hidden className="size-[18px]" />}
          </button>
          <a href="#/dashboard" aria-label="Dashboard" title="Dashboard" className={`${TOP_TILE} hidden sm:inline-grid`}>
            <LayoutDashboard aria-hidden className="size-[18px]" />
          </a>
          <span className="dg-tile inline-flex h-10 items-center gap-2.5 px-3.5">
            {snap?.night ? <Moon aria-label="Ban đêm" className="size-4 text-[#bdbdbd]" /> : <Clock aria-hidden className="size-4 text-[#bdbdbd]" />}
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
    <span className="inline-flex h-10 items-center gap-2.5 rounded-[10px] border border-solid border-white/20 bg-black/25 px-3.5 text-sm font-medium">
      <Volume2 aria-hidden className="size-[18px]" />
      Còi đang kêu
    </span>
  );
}

// ------------------------------------------------------------------ L0 / L1: status card

function StatusCard({ snap, level, rising }: { snap: HudSnapshot; level: Level; rising: boolean }) {
  const ordered = orderedReasons(snap.reasons);
  const primary = level > 0 ? (ordered[0] ?? null) : null;
  const Icon = (primary && REASON_ICONS[primary]) || CircleCheck;
  const headline = primary ? REASON_ACTIONS[primary] : level === 0 ? "Tỉnh táo" : LEVELS[level].title;
  const sub = level === 0 ? "Tiếp tục lái an toàn" : ordered.map(reasonText).join(" · ");
  const long = headline.split(" ").length > 3;
  const last = snap.alerts[0];
  const enroll = snap.enrollment?.status;

  return (
    <section
      aria-live={level ? "assertive" : "polite"}
      aria-atomic="true"
      className={`dg-alert ${level === 1 ? "l1" : "l0"} flex min-h-[46dvh] flex-col justify-between gap-6 px-6 pt-[22px] pb-5 lg:col-start-1 lg:row-start-1 lg:min-h-0`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="dg-card-title">
          <b>Trạng thái tài xế</b>
          <span>Cập nhật liên tục trên thiết bị</span>
        </span>
        {level === 1 ? (
          <span className="dg-chip">
            <CircleAlert aria-hidden className="size-4 text-hud-caution" strokeWidth={2.5} />
            {LEVELS[1].title}
          </span>
        ) : (
          <span className="dg-chip">
            <i />
            Đang giám sát
          </span>
        )}
      </div>

      {/* Re-mounted on every level / reason change, so the enter animation plays once per alert. */}
      <div
        key={`${level}:${primary ?? ""}`}
        className={`flex items-center gap-7 motion-reduce:animate-none ${rising ? "animate-hud-in-fast" : "animate-hud-in-slow"}`}
      >
        <div className={`dg-tile grid size-24 shrink-0 place-items-center !rounded-hud-xl ${level === 1 ? "text-hud-caution" : "text-hud-safe"}`}>
          <Icon aria-hidden className="size-12" strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <h1
            className={`m-0 leading-[1.05] font-semibold tracking-[-0.03em] text-balance ${
              long ? "text-[clamp(36px,4.6vw,58px)]" : "text-[clamp(40px,5.4vw,68px)]"
            }`}
          >
            {headline}
          </h1>
          <p className={`m-0 mt-2.5 text-xl ${level === 1 ? "text-[#e5d3a6]" : "text-[#bbd9c4]"}`}>{sub}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
        {snap.trip && <StatTile icon={Clock} value={durationText(snap.trip.drive_run_s)} label="Đã lái liên tục" />}
        <StatTile
          icon={History}
          value={last ? `${hourMinute(last.at)} · ${REASON_SHORT[orderedReasons(last.reasons)[0]] ?? LEVELS[last.level].title}` : "Không có"}
          label="Cảnh báo gần nhất"
        />
        {enroll && enroll !== "off" && (
          <StatTile
            icon={UserCheck}
            value={enroll === "done" ? "Đã đăng ký" : "Chưa đăng ký"}
            label={enroll === "done" ? "Tài xế" : "Dừng xe để đăng ký"}
          />
        )}
      </div>
    </section>
  );
}

function StatTile({ icon: Icon, value, label }: { icon: LucideIcon; value: string; label: string }) {
  return (
    <div className="dg-tile flex min-w-0 items-center gap-3 p-3">
      <span className="dg-tile grid size-[38px] shrink-0 place-items-center !rounded-[10px] text-[#d4d4d4]">
        <Icon aria-hidden className="size-[18px]" />
      </span>
      <span className="flex min-w-0 flex-col gap-0.5">
        <span className="dg-num truncate text-[17px] font-medium">{value}</span>
        <span className="text-xs text-hud-ink-3">{label}</span>
      </span>
    </div>
  );
}

// ------------------------------------------------------------------ L0 / L1: fatigue and numbers

function FatigueCard({ snap, level }: { snap: HudSnapshot; level: Level }) {
  const trip = snap.trip;
  const slots = trendSlots(trip);
  const summary = fatigueSummary(trip, snap.reasons, isDriving(snap));
  const minutes = trip?.window_min ?? slots.length;
  const distracted = level > 0 && snap.reasons.some(isDistractionReason);

  return (
    <section
      aria-label={`Độ mệt ${minutes} phút qua`}
      className={`dg-card grid gap-x-6 gap-y-3 px-6 py-5 lg:col-start-1 lg:row-start-2 ${slots.length ? "md:grid-cols-[minmax(0,1fr)_300px]" : ""}`}
    >
      <div className="flex items-start justify-between gap-3 md:col-span-2">
        <span className="dg-card-title">
          <b>Độ mệt và thông số</b>
          <span>{slots.length ? `${minutes} phút qua · mỗi cột 1 phút` : "Cập nhật liên tục"}</span>
        </span>
        {slots.length > 0 && (
          <span className="dg-chip" style={{ ["--dot" as string]: BAND_DOT[summary.band] }}>
            <i />
            {summary.text}
          </span>
        )}
      </div>

      {slots.length > 0 && trip && (
        <div
          role="img"
          aria-label={`Độ mệt từng phút: ${summary.text}`}
          className="relative flex h-[110px] items-end gap-[5px]"
        >
          <span aria-hidden className="absolute inset-x-0 border-t border-dashed border-hud-caution/35" style={{ bottom: `${trip.score_l1}%` }} />
          <span aria-hidden className="absolute left-0 text-[11px] text-hud-caution/70" style={{ bottom: `calc(${trip.score_l1}% + 4px)` }}>
            Nhắc nghỉ
          </span>
          {slots.map((s, i) =>
            s.kind === "score" ? (
              <div
                key={i}
                className={`flex-1 rounded-[3px] ${BAND_BG[s.band]} ${s.current ? "" : "opacity-85"}`}
                style={{ height: `${Math.max(4, Math.min(100, s.score))}%` }}
              />
            ) : (
              <div key={i} className={`flex-1 rounded-[3px] ${s.kind === "gap" ? "h-1.5 bg-white/12" : ""}`} />
            ),
          )}
        </div>
      )}

      <div
        aria-label="Thông số"
        className={`flex flex-col justify-center gap-2 ${slots.length ? "md:border-0 md:border-l md:border-solid md:border-white/7 md:pl-6" : ""}`}
      >
        <Meter label="Buồn ngủ" value={snap.drowsy_score} l1={trip?.score_l1} l2={trip?.score_l2} />
        <Meter label="Mất tập trung" value={snap.distraction_score} fill={distracted ? "var(--warning)" : undefined} />
        <span className="flex items-baseline justify-between">
          <span className="text-[13px] text-hud-ink-2">Mắt nhắm</span>
          <span className="dg-num text-base font-semibold">
            {formatNumber(snap.eyes_closed_s, 1)} <span className="text-xs font-normal text-hud-ink-3">giây</span>
          </span>
        </span>
      </div>
    </section>
  );
}

function Meter({ label, value, l1, l2, fill }: { label: string; value: number | undefined; l1?: number; l2?: number; fill?: string }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  const color = fill ?? (l1 != null && l2 != null ? BAND_DOT[fatigueBand(v, l1, l2)] : "var(--good)");
  return (
    <div className="flex flex-col gap-1">
      <span className="flex items-baseline justify-between">
        <span className="text-[13px] text-hud-ink-2">{label}</span>
        <span className="dg-num text-base font-semibold">
          {formatNumber(value)}
          <span className="text-xs font-normal text-hud-ink-3">/100</span>
        </span>
      </span>
      <span role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={v} className="dg-meter">
        <b style={{ width: `${v}%`, ["--fill" as string]: color }} />
        {l1 != null && <i aria-hidden style={{ left: `${l1}%`, background: "rgba(251,191,36,0.7)" }} />}
        {l2 != null && <i aria-hidden style={{ left: `${l2}%`, background: "rgba(248,113,113,0.7)" }} />}
      </span>
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
      className="dg-alert l2 flex min-h-[52dvh] flex-col justify-between gap-6 px-6 py-6 sm:px-8 lg:col-start-1 lg:row-start-1 lg:min-h-0"
    >
      <div className="flex items-start justify-between gap-3">
        <span className="flex flex-col gap-[3px]">
          <span className="text-base font-semibold">Trạng thái tài xế</span>
          <span className="text-[13px] opacity-70">Cập nhật liên tục trên thiết bị</span>
        </span>
        <span className="inline-flex items-center gap-2 rounded-hud-xs border border-solid border-hud-on-warning/18 bg-hud-on-warning/14 px-3 py-1.5 text-[13px] font-semibold">
          <TriangleAlert aria-hidden className="size-4" strokeWidth={2.5} />
          {LEVELS[2].title}
        </span>
      </div>

      <div
        key={`2:${primary ?? ""}`}
        className={`flex flex-col gap-6 motion-reduce:animate-none sm:flex-row sm:items-center sm:gap-9 ${rising ? "animate-hud-in-fast" : "animate-hud-in-slow"}`}
      >
        <div className="grid size-28 shrink-0 place-items-center rounded-hud-xl border border-solid border-hud-on-warning/18 bg-hud-on-warning/12 sm:size-[150px]">
          <Icon aria-hidden className="size-16 sm:size-20" strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <h1 className="m-0 text-[clamp(44px,7vw,92px)] leading-[0.98] font-bold tracking-[-0.035em] text-balance">{headline}</h1>
          <p className="m-0 mt-[18px] text-2xl font-medium opacity-80">{ordered.map(reasonText).join(" · ")}</p>
        </div>
      </div>

      <div className="flex flex-col gap-2.5">
        <div aria-label="Thông số" className="grid grid-cols-1 gap-2.5 sm:grid-cols-3">
          <WarnMeter className={tile} label="Buồn ngủ" value={snap.drowsy_score} />
          <WarnMeter className={tile} label="Mất tập trung" value={snap.distraction_score} />
          <div className={tile}>
            <span className="flex items-baseline justify-between gap-2">
              <span className="text-[13px] opacity-75">Mắt nhắm</span>
              <span className="dg-num text-[17px] font-bold">{formatNumber(snap.eyes_closed_s, 1)} giây</span>
            </span>
          </div>
        </div>
        {detail && <span className="text-sm opacity-70">{detail}</span>}
      </div>
    </section>
  );
}

function WarnMeter({ className, label, value }: { className: string; label: string; value: number | undefined }) {
  const v = Math.max(0, Math.min(100, value ?? 0));
  return (
    <div className={className}>
      <span className="flex items-baseline justify-between gap-2">
        <span className="text-[13px] opacity-75">{label}</span>
        <span className="dg-num text-[17px] font-bold">{formatNumber(value)}/100</span>
      </span>
      <span role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={100} aria-valuenow={v} className="mt-1.5 block h-[5px] rounded-full bg-hud-on-warning/16">
        <span className="block h-full rounded-full bg-hud-on-warning" style={{ width: `${v}%` }} />
      </span>
    </div>
  );
}

// ------------------------------------------------------------------ L3: the red screen, nothing else

function DangerStage({ reasons }: { reasons: Reason[] }) {
  const primary = orderedReasons(reasons)[0] ?? null;
  const [order, todo] = splitAction(primary ? REASON_ACTIONS[primary] : LEVELS[3].action);
  return (
    <main aria-live="assertive" aria-atomic="true" className="flex flex-col items-center justify-center gap-7 px-4 text-center sm:px-8">
      <span className="inline-flex items-center gap-2 rounded-[10px] border border-solid border-white/20 bg-black/25 px-4 py-2 text-base font-semibold tracking-[0.04em]">
        NGUY HIỂM
      </span>
      <OctagonAlert aria-hidden className="size-28 drop-shadow-[0_8px_30px_rgba(0,0,0,0.35)] sm:size-[150px]" strokeWidth={1.4} />
      <h1 className="m-0 flex flex-col items-center gap-3 text-[clamp(64px,10vw,128px)] leading-[0.95] font-bold tracking-[-0.04em]">
        {order}
        {todo && (
          <>
            {" "}
            <span className="text-[clamp(30px,4vw,52px)] leading-[1.1] font-semibold tracking-[-0.02em]">{todo}</span>
          </>
        )}
      </h1>
    </main>
  );
}

// ------------------------------------------------------------------ vehicle: speed, gear, turn signals

function SpeedCard({ snap, tall }: { snap: HudSnapshot; tall: boolean }) {
  const v = snap.vehicle;
  const speed = v ? v.speed_kmh : (snap.speed_kmh ?? 0); // null: link lost while driving, speed unknown
  const driving = isDriving(snap);
  const turn = v?.turn_signal ?? null;
  const lost = v?.signal_lost === true;
  const noSignal = v?.source === "sim" && !v.connected && !lost;
  const enrolling = ["look_camera", "look_road", "close_eyes"].includes(snap.enrollment?.status ?? "");
  const [sub, chip, dot] = lost
    ? [driving ? "Vẫn giám sát như đang chạy" : "Coi như đang đỗ", "Mất tín hiệu xe", "var(--warning)"]
    : noSignal
      ? ["Coi như đang đỗ", "Chưa có tín hiệu xe", "var(--series-1)"]
      : [
          !driving && enrolling ? "Xe đang đỗ · đang đăng ký khuôn mặt" : "Tín hiệu xe đã kết nối",
          driving ? "Đang chạy" : "Xe dừng",
          driving ? "var(--good)" : "var(--series-1)",
        ];

  return (
    <section
      aria-label="Xe"
      className={`dg-card flex min-h-0 flex-col gap-4 px-6 pt-[22px] pb-5 lg:col-start-2 lg:row-start-1 ${tall ? "lg:row-span-2" : ""}`}
    >
      <div className="flex items-start justify-between gap-3">
        <span className="dg-card-title">
          <b>Tốc độ</b>
          <span>{sub}</span>
        </span>
        <span className="dg-chip" style={{ ["--dot" as string]: dot }}>
          <i />
          {chip}
        </span>
      </div>

      <div className="grid min-h-0 flex-1 place-items-center">
        <div
          role="img"
          aria-label={speed == null ? "Tốc độ không rõ" : `Tốc độ ${Math.round(speed)} km/h`}
          className="relative aspect-[320/280] h-full max-h-[289px] max-w-full min-h-[180px] [container-type:size]"
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
            <rect x="104" y="227" width="112" height="24" fill="rgba(255,255,255,0.06)" />
          </svg>
          <div className="absolute inset-x-0 top-[26%] flex flex-col items-center gap-1.5">
            <span className="dg-num text-[33cqh] leading-[0.95] font-semibold tracking-[-0.03em]">
              {speed == null ? "– –" : Math.round(speed)}
            </span>
            <span className="text-base text-hud-ink-3">km/h</span>
          </div>
          <span className="absolute inset-x-0 top-[84%] grid place-items-center text-[15px] font-semibold text-[#d4d4d4]">
            {driving ? "D" : "P"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2.5">
        <TurnTile side="left" on={turn === "left"} />
        <div className="dg-tile flex flex-col items-center gap-1.5 px-2 py-3">
          <span className="dg-tile grid size-[38px] place-items-center !rounded-full text-[#d4d4d4]">
            <Car aria-hidden className="size-[18px]" />
          </span>
          <span className="text-xs text-hud-ink-2">{driving ? "Đang lái" : "Đang đỗ"}</span>
        </div>
        <TurnTile side="right" on={turn === "right"} />
      </div>
    </section>
  );
}

// Turn signal: amber arrow blinking like the car's own indicator (static with reduced motion).
function TurnTile({ side, on }: { side: "left" | "right"; on: boolean }) {
  const Icon = side === "left" ? ArrowBigLeft : ArrowBigRight;
  const name = `Xi nhan ${side === "left" ? "trái" : "phải"}`;
  return (
    <div role="img" aria-label={`${name}: ${on ? "đang bật" : "tắt"}`} className="dg-tile flex flex-col items-center gap-1.5 px-2 py-3">
      <span
        className={`grid size-[38px] place-items-center rounded-full border border-solid ${
          on ? "border-hud-turn/35 bg-hud-turn/12" : "border-white/10 bg-white/4"
        }`}
      >
        <Icon
          aria-hidden
          className={`size-5 ${on ? "fill-hud-turn text-hud-turn animate-hud-blink motion-reduce:animate-none" : "text-hud-ink-3"}`}
        />
      </span>
      <span className={`text-xs ${on ? "text-hud-ink-2" : "text-hud-ink-3"}`}>{name}</span>
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
      <footer className="flex justify-center px-4 pb-6 sm:px-8">
        {closed > 0 && (
          <span className="dg-num inline-flex items-center gap-3 rounded-[14px] border border-solid border-white/20 bg-black/28 px-6 py-3.5 text-[26px] font-semibold">
            <EyeOff aria-hidden className="size-[26px]" />
            Mắt nhắm {formatNumber(closed, 1)} giây
          </span>
        )}
      </footer>
    );
  }
  const left = target && snap ? (
    <FalseAlarmButton target={target} level={level} now={now} windowS={snap.feedback_window_s ?? 120} onPress={onFalseAlarm} />
  ) : (
    <span className="flex min-w-0 items-center gap-2.5 text-[15px] text-hud-ink-3">
      <Flag aria-hidden className="size-[18px] shrink-0" />
      <span className="min-w-0">{note ?? (snap ? noteFor(snap) : "Đang chờ dữ liệu từ thiết bị")}</span>
    </span>
  );
  return (
    <footer className={`grid items-center gap-3.5 px-4 pt-3.5 pb-5 sm:grid-cols-[minmax(0,1fr)_230px_230px] sm:px-8 ${className}`}>
      {left}
      {onAskDriver ? (
        <button type="button" onClick={onAskDriver} className="dg-btn">
          <span className="flex items-center gap-3">
            <UserRoundCog aria-hidden className="size-5" />
            Đổi tài xế
          </span>
          <ChevronRight aria-hidden className="size-4 text-hud-ink-3" />
        </button>
      ) : (
        <span className="hidden sm:block" />
      )}
      {onAskEnd ? (
        <button type="button" onClick={onAskEnd} disabled={ending} className="dg-btn">
          <span className="flex items-center gap-3">
            <FlagTriangleRight aria-hidden className="size-5" />
            {ending ? "Đang kết thúc…" : "Kết thúc chuyến"}
          </span>
          <ChevronRight aria-hidden className="size-4 text-hud-ink-3" />
        </button>
      ) : (
        <span className="hidden sm:block" />
      )}
    </footer>
  );
}

function noteFor(snap: HudSnapshot): string {
  const v = snap.vehicle;
  const last = snap.alerts[0];
  const lastAlert = last
    ? last.feedback
      ? `Đã ghi nhận: cảnh báo lúc ${hourMinute(last.at)} là sai`
      : `Cảnh báo gần nhất lúc ${hourMinute(last.at)} · ${reasonText(orderedReasons(last.reasons)[0])}`
    : null;
  return footerNote(snap, {
    signalLost: v?.signal_lost ? VEHICLE_SIGNAL_LOST_TEXT[v.driving ? "driving" : "parked"] : null,
    lowFps: "Xử lý chậm hơn 15 khung hình/giây · cảnh báo có thể trễ",
    phoneOff: `${PHONE_UNAVAILABLE_TEXT} · mắt và đầu vẫn được theo dõi`,
    enroll: enrollReminder(snap.enrollment),
    lastAlert,
  });
}

function FalseAlarmButton({ target, level, now, windowS, onPress }: { target: HudAlert; level: Level; now: number; windowS: number; onPress: () => void }) {
  const left = Math.max(0, Math.round(target.at + windowS - now));
  const ring = target.level >= 2 || level === 2 ? "ring-hud-warning/80" : "ring-hud-caution/70";
  return (
    <button type="button" onClick={onPress} className={`dg-btn justify-self-start !justify-start gap-3.5 ring-1 ${ring}`}>
      <Flag aria-hidden className="size-5 shrink-0" />
      <span className="flex flex-col gap-px">
        <span className="text-base font-medium">Cảnh báo này sai?</span>
        <span className="dg-num text-xs text-hud-ink-3">
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
          Chưa đăng ký tài xế
        </span>
      </div>
      <div className="flex items-center gap-6">
        <div className="dg-tile grid size-[88px] shrink-0 place-items-center !rounded-hud-xl text-[#93c5fd]">
          <ScanFace aria-hidden className="size-11" strokeWidth={1.75} />
        </div>
        <div className="min-w-0">
          <p className="m-0 text-[clamp(32px,4vw,48px)] leading-[1.08] font-semibold tracking-[-0.03em] text-balance">
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
        <div className="mt-auto grid gap-3 sm:grid-cols-[2fr_1fr]">
          <button
            type="button"
            onClick={() => onAnswer("enroll_start")}
            className="h-[60px] cursor-pointer rounded-hud-sm border-0 bg-[linear-gradient(180deg,#93c5fd_0%,#60a5fa_100%)] text-lg font-semibold text-[#0b1b33]"
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
      className="dg-alert sys grid min-h-0 gap-9 px-6 py-6 sm:px-8 lg:grid-cols-[minmax(0,1fr)_380px]"
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
                className={`h-2 w-12 rounded-full sm:w-[76px] ${i < index ? "bg-hud-safe" : i === index ? "bg-hud-system" : "bg-white/12"}`}
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
          <h1 className="m-0 text-[clamp(44px,6vw,76px)] leading-[1.02] font-semibold tracking-[-0.035em] text-balance">{text.title}</h1>
          <p className="m-0 text-[clamp(20px,2.2vw,26px)] text-[#b8c2d0]">{text.detail}</p>
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
        <FaceGuide step={step} hint={hint} />
        <span className="flex items-center gap-2.5 text-sm leading-[1.45] text-[#b8c2d0]">
          <Volume2 aria-hidden className="size-[18px] shrink-0 text-[#93c5fd]" />
          Đặt mặt vào khung oval. Hướng dẫn được đọc to, hết bước có tiếng bíp.
        </span>
      </div>
    </section>
  );
}

function enrollNote(e: HudEnrollment): string {
  const i = Math.max(0, ENROLL_STEP_ORDER.indexOf(enrollStep(e) as EnrollStep));
  const first = e.attempts > 0 ? `Làm lại ${e.attempts} lần` : i === 0 ? "Bước đầu tiên" : i === ENROLL_STEP_ORDER.length - 1 ? "Bước cuối" : `Bước ${i + 1}`;
  return `${first} · xe chạy thì việc đăng ký tạm dừng`;
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

/** "Bạn còn ở đó không?" (M44): the whole panel is one button, hit without aiming. Asked only while the
 *  camera cannot see the driver, so it never takes the eyes off the road of a driver who is watched. */
function PresencePanel({ unanswered, onAnswer }: { unanswered: boolean; onAnswer?: (action: VehicleAction) => void }) {
  return (
    <main className="grid p-4 sm:p-6">
      <button
        type="button"
        role="alert"
        onClick={() => onAnswer?.("presence_ok")}
        className={`grid w-full place-items-center rounded-hud-lg border-0 p-8 text-center font-hud ring-4 ${
          unanswered ? "bg-hud-danger text-white ring-white" : "bg-hud-surface text-hud-ink ring-hud-system"
        }`}
      >
        <span>
          <Hand aria-hidden strokeWidth={1.75} className="mx-auto size-24" />
          <span className="mt-6 block text-[clamp(32px,6vw,72px)] leading-tight font-extrabold text-balance">
            {PRESENCE_TEXT.title}
          </span>
          <span className="mt-4 block text-[clamp(22px,3vw,36px)] font-bold">{PRESENCE_TEXT.tap}</span>
          <span className="mt-3 block text-hud-body text-pretty opacity-80">
            {unanswered ? PRESENCE_TEXT.unanswered : PRESENCE_TEXT.detail}
          </span>
        </span>
      </button>
    </main>
  );
}

function SystemPanel({ state, edgeUrl, cause }: { state: SystemState; edgeUrl: string; cause: UnavailableCause | null }) {
  const Icon = SYSTEM_ICONS[state];
  // Unavailable: say what the driver can fix (camera covered, face too dark, ...), not only "no face".
  const text = state === "unavailable" && cause ? { ...SYSTEM_TEXT[state], detail: UNAVAILABLE_CAUSES[cause].detail } : SYSTEM_TEXT[state];
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
