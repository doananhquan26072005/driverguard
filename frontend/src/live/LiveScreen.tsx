// #/live: DriverGuard on the visitor's own camera, everything computed in this browser.
// The first page of the product: the login page (dashboard/Login.tsx; logging in or "Dùng thử không lưu"
// starts the camera at once) -> loading steps -> the in-car HUD fed by
// LiveAgent, with a small self-view so the driver can place the camera.
// M72: nothing here stops the monitoring with one touch. "Dừng camera" asks the HUD's "Kết thúc
// chuyến?" and ends the trip like that button; leaving the page with the trip running ends it too
// (summary and "ended" sent) and says aloud that the driver is no longer watched.
// M103: on a landscape screen the HUD sits scaled on the left and a column on the right holds the
// driver's camera and the driving panel (speed, turn signals), so the whole simulation is one page.
// Phones and upright screens keep the HUD full screen with the small floating camera.
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from "react";
import { Check, Gauge, Info, LoaderCircle, Minus, Plus, ScanFace, ShieldCheck, Square } from "lucide-react";
import { play, speak, systemSound } from "../hud/chime";
import HudScreen from "../hud/HudScreen";
import { STAGE_H, STAGE_W, StageFrame, stageLayout } from "../hud/HudStage";
import DrivePanel from "../drive/DrivePanel";
import { useCar } from "../drive/useCar";
import FaceOverlay from "./FaceOverlay";
import { NO_VIETNAMESE_VOICE_TEXT, useVietnameseVoice } from "../hud/voice";
import Login from "../dashboard/Login";
import { loadSession, saveSession } from "../lib/api";
import { perfDetail, perfLines, recoveryText, startupText } from "../lib/labels";
import type { HudEnrollment, Session } from "../lib/types";
import { LiveAgent, STEPS, type LiveStats, type Step, type VehicleSource } from "./agent";
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

const FACE_KEY = "driverguard.live.face"; // M104: the face drawing on the camera card, on unless switched off

function readFace(): boolean {
  try {
    return localStorage.getItem(FACE_KEY) !== "0";
  } catch {
    return true;
  }
}

function writeFace(on: boolean): void {
  try {
    localStorage.setItem(FACE_KEY, on ? "1" : "0");
  } catch {
    // storage unavailable: the choice just won't be remembered
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

/** A landscape screen (the HUD's 1280 x 800 stage): room for the column beside the HUD. */
function useWide(): boolean {
  const read = () => typeof window !== "undefined" && stageLayout(window.innerWidth, window.innerHeight)?.shape === "landscape";
  const [wide, setWide] = useState(read);
  useEffect(() => {
    const onResize = () => setWide(read());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return wide;
}

/** Docked: the HUD drawn on its 1280 x 800 stage and scaled into the room left of the column (as the
 *  guide's screens, M102). Not docked: no box at all, the HUD is the screen. Always the same elements,
 *  so the HUD is not mounted again when the window changes shape. */
function HudBox({ docked, children }: { docked: boolean; children: ReactNode }) {
  const room = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(0);
  useEffect(() => {
    if (!docked) return;
    const fit = () => {
      const r = room.current;
      setScale(r ? Math.min(r.clientWidth / STAGE_W, r.clientHeight / STAGE_H) : 0);
    };
    fit();
    const seen = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(fit);
    if (seen && room.current) seen.observe(room.current);
    window.addEventListener("resize", fit);
    return () => {
      seen?.disconnect();
      window.removeEventListener("resize", fit);
    };
  }, [docked]);
  // transform: also the containing block of the HUD's `fixed` dialogs. The two type sizes that follow
  // the window's width (index.css) are pinned to what a 1280 px screen gives.
  const screen: CSSProperties | undefined = docked
    ? {
        width: STAGE_W,
        height: STAGE_H,
        transform: `scale(${scale})`,
        transformOrigin: "top left",
        ["--text-hud-title" as string]: "30px",
        ["--text-hud-display" as string]: "76.8px",
      }
    : undefined;
  return (
    <div ref={room} className={docked ? "live-hud" : "contents"}>
      <div className={docked ? "live-hud-screen" : "contents"} style={docked ? { width: STAGE_W * scale, height: STAGE_H * scale } : undefined}>
        <div style={screen} className={docked ? "" : "contents"}>
          <StageFrame.Provider value={docked ? { width: STAGE_W, height: STAGE_H } : null}>{children}</StageFrame.Provider>
        </div>
      </div>
    </div>
  );
}

const SIDE_W = 380; // px of the column's design, before it is scaled

/** The column beside the HUD, laid out at SIDE_W and scaled down as a whole when the window is too
 *  short for it (the camera keeps its 4:3 picture, as in the user's design of 12/10). Not docked: no
 *  box at all. Always the same elements: the self-view's <video> inside must not be mounted again. */
function SideColumn({ docked, children }: { docked: boolean; children: ReactNode }) {
  const room = useRef<HTMLElement>(null);
  const content = useRef<HTMLDivElement>(null);
  const [scale, setScale] = useState(1);
  useEffect(() => {
    if (!docked) return;
    const fit = () => {
      const r = room.current;
      const c = content.current;
      if (r && c && c.offsetHeight > 0) setScale(Math.min(1, r.clientHeight / c.offsetHeight));
    };
    fit();
    const seen = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(fit);
    if (seen && room.current) seen.observe(room.current);
    if (seen && content.current) seen.observe(content.current);
    window.addEventListener("resize", fit);
    return () => {
      seen?.disconnect();
      window.removeEventListener("resize", fit);
    };
  }, [docked]);
  return (
    <aside ref={room} aria-label={docked ? "Camera và điều khiển xe" : undefined} className={docked ? "live-side" : "contents"} style={docked ? { width: SIDE_W * scale } : undefined}>
      <div
        ref={content}
        className={docked ? "live-side-content" : "contents"}
        style={docked ? { width: SIDE_W, transform: `scale(${scale})`, transformOrigin: "top left" } : undefined}
      >
        {children}
      </div>
    </aside>
  );
}

const SOURCE_TEXT: Record<VehicleSource, string> = {
  panel: "Đang đưa vào giám sát",
  remote: "Đang nhận từ #/drive trên thiết bị khác",
  sim: "Đang dùng trình mô phỏng ở terminal · bấm để lái ở đây",
  none: "Bấm một nút để bắt đầu lái",
};

/** The driving panel beside the HUD (M103): its car goes straight to this page's agent, no backend in
 *  between (works offline and in the try-out). #/drive on another device, paired by the code, still
 *  works and wins while it is sending. */
function SidePanel({ agent }: { agent: LiveAgent }) {
  const { car, carRef, act, touched } = useCar();
  useEffect(() => {
    agent.usePanel(() => (touched ? carRef.current : null));
    return () => agent.usePanel(null);
  }, [agent, touched, carRef]);
  const [from, setFrom] = useState<VehicleSource>(agent.vehicleFrom);
  useEffect(() => {
    const id = setInterval(() => setFrom(agent.vehicleFrom), 500);
    return () => clearInterval(id);
  }, [agent]);
  return (
    <section aria-label="Điều khiển xe" className="grid shrink-0 gap-3 rounded-hud-sm border border-solid border-white/10 bg-white/[0.03] p-3">
      <header className="flex items-center gap-2 px-1">
        <Gauge aria-hidden className="size-5 text-hud-system" />
        <h2 className="m-0 text-[19px] font-semibold">Điều khiển xe</h2>
        <a
          href={`#/drive?code=${agent.driveCode}`}
          target="_blank"
          rel="noopener"
          aria-label={`Điều khiển xe · mã ${agent.driveCode}`}
          title="Mở trang điều khiển xe trên thiết bị khác (điện thoại) với mã này"
          className="ml-auto dg-chip !text-[14px] tabular-nums text-hud-ink no-underline"
        >
          Mã {agent.driveCode}
        </a>
      </header>
      <DrivePanel
        side
        car={car}
        act={act}
        status={
          <span role="status" className={`text-[14px] ${from === "remote" ? "text-hud-system" : "text-hud-ink-3"}`}>
            {SOURCE_TEXT[from]}
          </span>
        }
      />
    </section>
  );
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
  const wide = useWide();

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

  // "Xong" on the trip summary. A driver who is logged in goes on to the Dashboard (its overview has
  // "Bắt đầu ca lái" for the next trip, 13/10); the try-out has no account, so back to the first page.
  async function stop() {
    await agent?.stop();
    setAgent(null);
    setStep(null);
    if (session && !guest) window.location.hash = "#/dashboard";
  }

  // #/live?start (the Dashboard's "Bắt đầu ca lái"): a driver who is logged in starts at once, without
  // the first page's button. The address loses `start`, so a reload does not start a trip by itself.
  useEffect(() => {
    if (!new URLSearchParams(window.location.hash.split("?")[1] ?? "").has("start")) return;
    window.history.replaceState(null, "", "#/live");
    if (session?.role === "driver") void start(session);
    // once, on arrival: the address is read before anything else changes it
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function logout() {
    saveSession(null);
    setSession(null);
  }

  const ready = agent != null;
  const docked = wide && ready; // M103: the HUD, the camera and the driving panel side by side
  return (
    // The same elements in both layouts (only their classes change): the <video> holds the camera
    // stream and must never be mounted again.
    <div className={docked ? "live-shell font-hud text-hud-ink antialiased [color-scheme:dark]" : "contents"}>
      {docked && (
        <header className="live-bar">
          <span className="brand-mark" aria-hidden>
            <ShieldCheck size={20} strokeWidth={2.25} />
          </span>
          {/* Not an h1: the HUD's alert is the page's heading. */}
          <strong className="live-title">DriverGuard</strong>
          <p>Màn hình tài xế · bản chạy trong trình duyệt (#/live)</p>
        </header>
      )}
      <div className={docked ? "live-body" : "contents"}>
        <HudBox docked={docked}>{ready && <HudScreen source={agent} onTripEnded={() => setEnded(true)} onDone={stop} askEnd={askEnd} />}</HudBox>
        <SideColumn docked={docked}>
          {docked && (
            <p role="note" className="live-side-note">
              <Info aria-hidden className="size-4 shrink-0" />
              Phần này chỉ hiện khi mô phỏng ứng dụng, khi lái thật sẽ không có.
            </p>
          )}
          {docked && <p className="live-side-label">Camera tài xế</p>}
          <SelfView videoRef={videoRef} agent={ended ? null : agent} docked={docked} onStop={() => setAskEnd((n) => n + 1)} />
          {docked && !ended && <SidePanel agent={agent} />}
        </SideColumn>
      </div>
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
    </div>
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
  docked,
  onStop,
}: {
  videoRef: React.RefObject<HTMLVideoElement | null>;
  agent: LiveAgent | null;
  docked: boolean; // M103: a card in the column beside the HUD, not a floating frame
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
  const compact = !docked && stats?.level === 3; // docked, it does not sit over the HUD
  const [tech, setTech] = useState(readTech);
  const [faceOn, setFaceOn] = useState(readFace);
  const toggleFace = () => {
    setFaceOn(!faceOn);
    writeFace(!faceOn);
  };
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
  const width = Math.max(SELF_VIEW_WIDTHS[place.size], tech && !docked ? TECH_WIDTH_PX : 0);
  const placed = !docked && place.x != null && place.y != null;
  const faceLine = (
    <span className={`inline-flex items-center gap-1.5 ${m?.face ? "" : "text-hud-caution"}`}>
      <span aria-hidden className="size-1.5 shrink-0 rounded-full bg-[#f87171]" />
      {m?.face ? "Chỉ xem, không lưu" : "Không thấy mặt"}
    </span>
  );
  const floating: React.CSSProperties = docked ? {} : { ...(compact ? {} : { width }), ...(placed ? { left: place.x!, top: place.y!, bottom: "auto" } : {}) };

  return (
    <div
      ref={box}
      data-testid="self-view"
      data-docked={docked || undefined}
      style={floating}
      className={`${
        docked ? "relative w-full" : "fixed bottom-4 left-4 z-40 shadow-[0_24px_48px_rgba(0,0,0,0.45)] backdrop-blur"
      } overflow-hidden rounded-hud-sm border border-solid border-white/15 bg-black/85 font-hud text-white ${compact ? "w-auto" : ""} ${
        agent || docked ? "" : "pointer-events-none opacity-0"
      }`}
    >
      {/* Kept mounted (it holds the stream), only hidden at L3. Small (M64): it sits over the HUD.
          Docked (M103), it is a card beside the HUD and is neither dragged nor resized. */}
      <video
        ref={videoRef}
        onPointerDown={docked ? undefined : onGrab}
        onPointerMove={docked ? undefined : onDrag}
        onPointerUp={docked ? undefined : onDrop}
        onPointerCancel={docked ? undefined : onDrop}
        title={docked ? undefined : "Kéo để dời khung camera"}
        className={`aspect-[4/3] w-full -scale-x-100 object-cover ${docked ? "" : "cursor-grab touch-none active:cursor-grabbing"} ${compact ? "hidden" : "block"}`}
        muted
        playsInline
      />
      {/* M104: the driver's face drawn over the picture, beside the HUD only (the simulation). */}
      {docked && agent && faceOn && <FaceOverlay agent={agent} />}
      {docked && !agent && <p className="m-0 p-3 text-[13px] text-white/70">Đã kết thúc chuyến · camera tắt</p>}
      {agent && compact && (
        <button type="button" onClick={onStop} className="inline-flex min-h-10 items-center gap-1 rounded-full border-0 bg-transparent px-4 text-[13px] font-semibold text-white">
          <Square aria-hidden className="size-3.5" /> Dừng camera
        </button>
      )}
      {agent && !compact && (
        <div className={`grid shrink-0 gap-1.5 tabular-nums ${docked ? "absolute inset-x-0 bottom-0 bg-[linear-gradient(0deg,rgba(0,0,0,0.75),rgba(0,0,0,0))] px-3 pt-6 pb-2 text-[13px] leading-snug" : "p-2 text-[12px] leading-tight"}`}>
          {!docked && faceLine}
          {tech && !docked && (
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
            {docked ? (
              // One row with the buttons; the pairing code is on the driving panel below.
              <span className="flex-1">{faceLine}</span>
            ) : (
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
            )}
            {!docked && (
              <>
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
              </>
            )}
            {/* The engineers' numbers only on the floating frame: beside the HUD the camera is a
                picture to place the face by (the user's choice, 12/10). */}
            {!docked && (
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
            )}
            {docked && (
              <button
                type="button"
                onClick={toggleFace}
                aria-pressed={faceOn}
                aria-label={faceOn ? "Ẩn khung nhận diện mặt" : "Hiện khung nhận diện mặt"}
                title={faceOn ? "Ẩn khung nhận diện mặt" : "Hiện khung nhận diện mặt"}
                className={`grid size-9 place-items-center rounded-full border-0 text-white ${faceOn ? "bg-hud-system/45" : "bg-white/10"}`}
              >
                <ScanFace aria-hidden className="size-4" />
              </button>
            )}
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
