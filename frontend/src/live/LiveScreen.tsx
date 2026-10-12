// #/live: DriverGuard on the visitor's own camera, everything computed in this browser.
// The first page of the product: the login page (dashboard/Login.tsx; logging in or "Dùng thử không lưu"
// starts the camera at once) -> loading steps -> the in-car HUD fed by
// LiveAgent, with a small self-view so the driver can place the camera.
// M72: nothing here stops the monitoring with one touch. "Dừng camera" asks the HUD's "Kết thúc
// chuyến?" and ends the trip like that button; leaving the page with the trip running ends it too
// (summary and "ended" sent) and says aloud that the driver is no longer watched.
import { useEffect, useRef, useState } from "react";
import { Check, Gauge, Info, LoaderCircle, Minus, Plus, ShieldCheck, Square } from "lucide-react";
import { play, speak, systemSound } from "../hud/chime";
import HudScreen from "../hud/HudScreen";
import { NO_VIETNAMESE_VOICE_TEXT, useVietnameseVoice } from "../hud/voice";
import Login from "../dashboard/Login";
import { loadSession, saveSession } from "../lib/api";
import { perfDetail, perfLines, recoveryText, startupText } from "../lib/labels";
import type { HudEnrollment, Session } from "../lib/types";
import { LiveAgent, STEPS, type LiveStats, type Step } from "./agent";
import { HUD_DEFAULTS } from "../lib/defaults";
import { SELF_VIEW_WIDTHS, clampCorner, readPlace, resized, writePlace, type SelfViewPlace } from "./selfView";

function cameraError(err: unknown): string {
  const name = (err as DOMException)?.name;
  if (name === "NotAllowedError") return "Bạn chưa cho phép dùng camera. Bấm biểu tượng camera trên thanh địa chỉ để cho phép, rồi thử lại.";
  if (name === "NotFoundError") return "Không tìm thấy camera trên máy này.";
  if (name === "NotReadableError") return "Camera đang được ứng dụng khác dùng (Zoom, Meet…). Đóng ứng dụng đó rồi thử lại.";
  if (!window.isSecureContext) return "Trình duyệt chỉ cho dùng camera trên trang https.";
  return `Không khởi động được: ${String((err as Error)?.message ?? err)}`;
}

const TECH_KEY = "driverguard.live.tech"; // per-browser convenience only
const TECH_WIDTH_PX = 240; // the technical lines need this much, whatever size the frame was given

function readTech(): boolean {
  try {
    return localStorage.getItem(TECH_KEY) === "1";
  } catch {
    return false;
  }
}

function writeTech(on: boolean): void {
  try {
    localStorage.setItem(TECH_KEY, on ? "1" : "0");
  } catch {
    // storage unavailable (private mode): the toggle just won't be remembered
  }
}

// Self-view line: how long enrollment took and how many steps were redone (to judge it in a test).
function enrollText(e: HudEnrollment): string {
  const redo = e.attempts ? ` · làm lại ${e.attempts}` : "";
  if (e.status === "done") return `Làm quen xong ${e.duration_s?.toFixed(1) ?? "–"} s${redo}`;
  if (e.status === "failed") return `Làm quen chưa được${redo}`;
  if (e.status === "waiting") return "Chưa làm quen (xe đang chạy)";
  const step = ["look_camera", "look_road", "close_eyes"].indexOf(e.status) + 1;
  return `Làm quen bước ${step}/3 · ${Math.round(e.progress * 100)}%${redo}`;
}

export default function LiveScreen() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [session, setSession] = useState<Session | null>(loadSession);
  const [guest, setGuest] = useState(false);
  const [step, setStep] = useState<Step | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agent, setAgent] = useState<LiveAgent | null>(null);
  const [ended, setEnded] = useState(false); // trip ended: the summary is on screen, the camera is off
  const [askEnd, setAskEnd] = useState(0); // "Dừng camera": each press asks the HUD's end-of-trip question
  const voice = useVietnameseVoice();

  useEffect(
    () => () => {
      if (!agent?.running) return; // the trip was ended on the HUD: nothing left to stop
      // Back button, another address: the page goes, and the monitoring with it. Not silently.
      play(systemSound("monitoring_stopped"));
      setTimeout(() => speak("sys.stopped"), HUD_DEFAULTS.chime_to_voice_s * 1000); // the line follows the chime
      void agent.endTrip().catch(() => agent.stop());
    },
    [agent],
  );

  // The tab is closed or reloaded with the trip running (M100). Before: no summary, no "ended", and the
  // fleet saw the vehicle "lost" 90 s later. The browser asks before it goes, and when the page does go
  // the trip is ended in that same turn (LiveAgent.leave): nothing asynchronous would finish any more.
  useEffect(() => {
    if (!agent) return;
    const ask = (e: BeforeUnloadEvent) => {
      if (!agent.running) return;
      e.preventDefault();
      e.returnValue = ""; // the browser shows its own "leave this page?" question
    };
    const leave = () => void (agent.running && agent.leave());
    window.addEventListener("beforeunload", ask);
    window.addEventListener("pagehide", leave);
    return () => {
      window.removeEventListener("beforeunload", ask);
      window.removeEventListener("pagehide", leave);
    };
  }, [agent]);

  // `who`: the account the trip is saved to, or null for a try-out (nothing saved, nothing sent).
  async function start(who: Session | null) {
    if (!videoRef.current) return;
    setError(null);
    setEnded(false);
    setGuest(who == null);
    setStep({ step: "camera", progress: 0 }); // the loading screen from the press, not from the first answer
    try {
      setAgent(await LiveAgent.start(videoRef.current, who, setStep));
    } catch (err) {
      setError(cameraError(err));
      setStep(null);
    }
  }

  // Logged in on the first page: a driver goes straight to the camera; the other roles have no trip to
  // drive, their next page is the dashboard.
  function entered(s: Session) {
    saveSession(s);
    if (s.role !== "driver") {
      window.location.hash = "#/dashboard";
      return;
    }
    setSession(s);
    void start(s);
  }

  async function stop() {
    await agent?.stop();
    setAgent(null);
    setStep(null);
  }

  function logout() {
    saveSession(null);
    setSession(null);
  }

  const ready = agent != null;
  return (
    <>
      {ready && <HudScreen source={agent} onTripEnded={() => setEnded(true)} onDone={stop} askEnd={askEnd} />}
      <SelfView videoRef={videoRef} agent={ended ? null : agent} onStop={() => setAskEnd((n) => n + 1)} />
      {!ready && !step && (
        // The product's first page: the one login page (dashboard/Login.tsx). Logging in or "Dùng thử
        // không lưu" goes straight on: the camera is asked for and the loading steps start.
        <Login
          onLogin={entered}
          live={{
            session,
            onStart: () => void start(session),
            onGuest: () => void start(null),
            onSwitch: logout,
            note: (
              <>
                {voice === false && (
                  <p role="note" className="form-note">
                    {NO_VIETNAMESE_VOICE_TEXT}
                  </p>
                )}
                {error && (
                  <p role="alert" className="form-error">
                    {error}
                  </p>
                )}
              </>
            ),
          }}
        />
      )}
      {!ready && step && (
        <div className="guide live-setup font-hud text-hud-ink antialiased [color-scheme:dark]">
          <header className="guide-bar">
            <span className="brand-mark" aria-hidden>
              <ShieldCheck size={20} strokeWidth={2.25} />
            </span>
            <h1>DriverGuard</h1>
          </header>
          <main className="guide-main live-loading">
            <section className="live-panel dg-card">
              <span className="dg-card-title">
                <b className="!text-xl !font-semibold">Đang khởi động</b>
                <span>{guest || !session ? "Dùng thử · không lưu, không gửi số liệu giám sát" : `Lưu vào tài khoản ${session.username}`}</span>
              </span>
              <Progress step={step} />
              <p className="m-0 text-[13px] leading-relaxed text-hud-ink-3">
                Mọi thứ được tải về và chạy ngay trong trình duyệt này. Không có hình ảnh nào được gửi lên máy chủ.
              </p>
            </section>
          </main>
        </div>
      )}
    </>
  );
}

function Progress({ step }: { step: Step }) {
  const order = Object.keys(STEPS) as (keyof typeof STEPS)[];
  const current = step.step === "ready" ? order.length : order.indexOf(step.step);
  const pct = Math.round(step.progress * 100);
  return (
    <ol className="m-0 grid list-none gap-2.5 p-0" aria-live="polite">
      {order.map((s, i) => (
        <li key={s} className={`grid gap-3 rounded-hud-sm px-4 py-3.5 ${i === current ? "border border-solid border-[#93c5fd]/45 bg-hud-system/8" : "dg-tile"}`}>
          <div className="flex items-center gap-3">
            {i < current ? (
              <Check aria-hidden className="size-5 text-hud-safe" strokeWidth={2.25} />
            ) : i === current ? (
              <LoaderCircle aria-hidden className="size-5 animate-spin text-[#93c5fd]" />
            ) : (
              <span aria-hidden className="grid size-5 place-items-center">
                <span className="size-2 rounded-full bg-white/20" />
              </span>
            )}
            <span className={`text-base font-medium ${i <= current ? "text-hud-ink" : "text-hud-ink-3"}`}>{STEPS[s]}</span>
            <span className={`dg-num ml-auto text-[13px] ${i < current ? "text-hud-safe" : "text-[#b8c2d0]"}`}>
              {i < current ? "Xong" : s === "prepare" && i === current ? `${pct}%` : ""}
            </span>
          </div>
          {s === "prepare" && i === current && (
            <div role="progressbar" aria-label="Đang chuẩn bị" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} className="h-2 overflow-hidden rounded-full bg-white/8">
              <div
                className="h-full origin-left rounded-full bg-[linear-gradient(90deg,#60a5fa,#93c5fd)] transition-transform duration-300"
                style={{ transform: `scaleX(${Math.max(step.progress, 0.05)})` }}
              />
            </div>
          )}
        </li>
      ))}
      <li className="dg-tile flex items-center gap-3 px-4 py-3.5 opacity-70">
        <span aria-hidden className="grid size-5 place-items-center">
          <span className="size-2 rounded-full bg-white/20" />
        </span>
        <span className="text-base font-medium text-hud-ink-3">Sẵn sàng giám sát</span>
      </li>
    </ol>
  );
}

/** Small mirror of the driver's own camera (local only) with a plain status and a stop button
 * (which asks first, and ends the trip: M72).
 * The measurements (EAR, angles, FPS, YOLO time) are for engineers: hidden unless "Chi tiết kỹ thuật"
 * is switched on (remembered in this browser). At L3 it shrinks to the stop button. */
function SelfView({
  videoRef,
  agent,
  onStop,
}: {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  agent: LiveAgent | null;
  onStop: () => void;
}) {
  const [stats, setStats] = useState<LiveStats | null>(null);
  useEffect(() => {
    if (!agent) return;
    const id = setInterval(() => setStats(agent.getStats()), 500);
    return () => clearInterval(id);
  }, [agent]);
  const m = stats?.measures;
  const fmt = (v: number | null | undefined, d = 2) => (v == null ? "–" : v.toFixed(d));
  const compact = stats?.level === 3;
  const [tech, setTech] = useState(readTech);
  const toggleTech = () => {
    setTech(!tech);
    writeTech(!tech);
  };

  // M100: the frame can be dragged anywhere (by its picture) and made smaller or larger, so it no
  // longer has to sit on a button of the HUD. Its place is kept in this browser.
  const box = useRef<HTMLDivElement>(null);
  const [place, setPlace] = useState<SelfViewPlace>(readPlace);
  const grab = useRef<{ dx: number; dy: number } | null>(null);
  const cornerAt = (x: number, y: number) => {
    const el = box.current;
    return el ? clampCorner(x, y, { width: el.offsetWidth, height: el.offsetHeight }, { width: window.innerWidth, height: window.innerHeight }) : { x, y };
  };
  const onGrab = (e: React.PointerEvent<HTMLElement>) => {
    const el = box.current;
    if (!el) return;
    const r = el.getBoundingClientRect();
    grab.current = { dx: e.clientX - r.left, dy: e.clientY - r.top };
    e.currentTarget.setPointerCapture?.(e.pointerId);
  };
  const onDrag = (e: React.PointerEvent<HTMLElement>) => {
    if (!grab.current) return;
    const corner = cornerAt(e.clientX - grab.current.dx, e.clientY - grab.current.dy);
    setPlace((p) => ({ ...p, ...corner }));
  };
  const onDrop = () => {
    if (!grab.current) return;
    grab.current = null;
    setPlace((p) => (writePlace(p), p));
  };
  const resize = (step: 1 | -1) => setPlace((p) => {
    const next = { ...p, size: resized(p.size, step) };
    writePlace(next);
    return next;
  });
  // A window that got smaller, or a frame that got larger: back into view.
  useEffect(() => {
    const fit = () => setPlace((p) => (p.x == null || p.y == null ? p : { ...p, ...cornerAt(p.x, p.y) }));
    fit();
    window.addEventListener("resize", fit);
    return () => window.removeEventListener("resize", fit);
  }, [place.size, tech, compact]);
  const width = Math.max(SELF_VIEW_WIDTHS[place.size], tech ? TECH_WIDTH_PX : 0);
  const placed = place.x != null && place.y != null;

  return (
    <div
      ref={box}
      data-testid="self-view"
      style={{ ...(compact ? {} : { width }), ...(placed ? { left: place.x!, top: place.y!, bottom: "auto" } : {}) }}
      className={`fixed bottom-4 left-4 z-40 overflow-hidden rounded-hud-sm border border-solid border-white/15 bg-black/85 font-hud text-white shadow-[0_24px_48px_rgba(0,0,0,0.45)] backdrop-blur ${
        compact ? "w-auto" : ""
      } ${agent ? "" : "pointer-events-none opacity-0"}`}
    >
      {/* Kept mounted (it holds the stream), only hidden at L3. Small (M64): it sits over the HUD. */}
      <video
        ref={videoRef}
        onPointerDown={onGrab}
        onPointerMove={onDrag}
        onPointerUp={onDrop}
        onPointerCancel={onDrop}
        title="Kéo để dời khung camera"
        className={`aspect-[4/3] w-full -scale-x-100 cursor-grab touch-none object-cover active:cursor-grabbing ${compact ? "hidden" : "block"}`}
        muted
        playsInline
      />
      {agent && compact && (
        <button type="button" onClick={onStop} className="inline-flex min-h-10 items-center gap-1 rounded-full border-0 bg-transparent px-4 text-[13px] font-semibold text-white">
          <Square aria-hidden className="size-3.5" /> Dừng camera
        </button>
      )}
      {agent && !compact && (
        <div className="grid gap-1.5 p-2 text-[12px] leading-tight tabular-nums">
          <span className={`inline-flex items-center gap-1.5 ${m?.face ? "" : "text-hud-caution"}`}>
            <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-[#f87171]" />
            {m?.face ? "Chỉ xem, không lưu" : "Không thấy mặt"}
          </span>
          {tech && (
            <>
              <span className="text-white/70">
                EAR {fmt(m?.ear)} · {fmt(stats?.fps, 0)} FPS
              </span>
              <span className="text-white/70">
                Yaw {fmt(m?.yaw, 0)}° · Pitch {fmt(m?.pitch, 0)}° · ĐT{" "}
                {stats?.phoneOn ? `${m?.phone ? "có" : "không"} (${fmt(stats.yoloMs, 0)} ms)` : "tắt"}
              </span>
              {stats?.perf?.stages_ms.total && (
                <span
                  className="whitespace-pre-line text-white/70"
                  title={[perfDetail(stats.perf), startupText(stats.startup)].filter(Boolean).join("\n")}
                  // The same numbers as JSON, for bench/live.bench.mjs (M67). Timings and counts only.
                  data-perf={JSON.stringify({ perf: stats.perf, totals: stats.totals, startup: stats.startup, fps: stats.fps, recovery: stats.recovery })}
                >
                  {perfLines(stats.perf)}
                </span>
              )}
              {stats?.enrollment && stats.enrollment.status !== "off" && (
                <span className="text-white/70">{enrollText(stats.enrollment)}</span>
              )}
              {stats && recoveryText(stats.recovery) && <span className="text-hud-caution">{recoveryText(stats.recovery)}</span>}
              {stats?.lastError && <span className="break-all text-hud-caution">Lỗi gần nhất: {stats.lastError}</span>}
              {stats && stats.sent > 0 && <span className="text-white/70">Đã lưu {stats.sent} cảnh báo</span>}
            </>
          )}
          {stats?.sendError && <span className="text-hud-caution">{stats.sendError}</span>}
          <div className="flex flex-wrap items-center gap-1">
            <a
              href={`#/drive?code=${agent.driveCode}`}
              target="_blank"
              rel="noopener"
              aria-label={`Điều khiển xe · mã ${agent.driveCode}`}
              title="Mở trang điều khiển xe (tốc độ, xi nhan) cho phiên này"
              className="inline-flex min-h-9 flex-1 items-center justify-center gap-1 rounded-full bg-hud-system/25 px-2 text-[12px] font-semibold text-white no-underline"
            >
              <Gauge aria-hidden className="size-3.5" /> {agent.driveCode}
            </a>
            <button
              type="button"
              onClick={() => resize(-1)}
              disabled={place.size === 0}
              aria-label="Thu nhỏ khung camera"
              title="Thu nhỏ khung camera"
              className="grid size-9 place-items-center rounded-full border-0 bg-white/10 text-white disabled:opacity-40"
            >
              <Minus aria-hidden className="size-4" />
            </button>
            <button
              type="button"
              onClick={() => resize(1)}
              disabled={place.size === SELF_VIEW_WIDTHS.length - 1}
              aria-label="Phóng to khung camera"
              title="Phóng to khung camera"
              className="grid size-9 place-items-center rounded-full border-0 bg-white/10 text-white disabled:opacity-40"
            >
              <Plus aria-hidden className="size-4" />
            </button>
            <button
              type="button"
              onClick={toggleTech}
              aria-pressed={tech}
              aria-label={tech ? "Ẩn chi tiết kỹ thuật" : "Chi tiết kỹ thuật"}
              title={tech ? "Ẩn chi tiết kỹ thuật" : "Chi tiết kỹ thuật"}
              className="grid size-9 place-items-center rounded-full border-0 bg-white/10 text-white"
            >
              <Info aria-hidden className="size-4" />
            </button>
            <button
              type="button"
              onClick={onStop}
              aria-label="Dừng camera"
              title="Dừng camera và kết thúc ca lái"
              className="grid size-9 place-items-center rounded-full border-0 bg-white/10 text-white"
            >
              <Square aria-hidden className="size-3.5" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
