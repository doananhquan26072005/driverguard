// #/live: DriverGuard on the visitor's own camera, everything computed in this browser.
// Setup (who is driving, face enrollment, privacy) -> loading steps -> the in-car HUD fed by
// LiveAgent, with a small self-view so the driver can place the camera.
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Camera, Check, Gauge, Info, LoaderCircle, LogOut, ShieldCheck, Square } from "lucide-react";
import HudScreen from "../hud/HudScreen";
import { NO_VIETNAMESE_VOICE_TEXT, useVietnameseVoice } from "../hud/voice";
import { ApiError, loadSession, login, saveSession } from "../lib/api";
import { perfDetail, perfLines, startupText } from "../lib/labels";
import type { HudEnrollment, Session } from "../lib/types";
import { LiveAgent, STEPS, type LiveStats, type Step } from "./agent";

const BTN =
  "inline-flex min-h-12 items-center justify-center gap-2 rounded-full border-0 px-5 text-hud-label font-semibold transition-colors disabled:opacity-50";
const INPUT =
  "min-h-12 w-full rounded-hud-sm border-0 bg-hud-raised px-4 text-hud-label text-hud-ink ring-1 ring-hud-line focus:outline-2 focus:outline-hud-system";

function cameraError(err: unknown): string {
  const name = (err as DOMException)?.name;
  if (name === "NotAllowedError") return "Bạn chưa cho phép dùng camera. Bấm biểu tượng camera trên thanh địa chỉ để cho phép, rồi thử lại.";
  if (name === "NotFoundError") return "Không tìm thấy camera trên máy này.";
  if (name === "NotReadableError") return "Camera đang được ứng dụng khác dùng (Zoom, Meet…). Đóng ứng dụng đó rồi thử lại.";
  if (!window.isSecureContext) return "Trình duyệt chỉ cho dùng camera trên trang https.";
  return `Không khởi động được: ${String((err as Error)?.message ?? err)}`;
}

const TECH_KEY = "driverguard.live.tech"; // per-browser convenience only

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
  if (e.status === "done") return `Đăng ký xong ${e.duration_s?.toFixed(1) ?? "–"} s${redo}`;
  if (e.status === "failed") return `Đăng ký chưa được${redo}`;
  if (e.status === "waiting") return "Chưa đăng ký (xe đang chạy)";
  const step = ["look_camera", "look_road", "close_eyes"].indexOf(e.status) + 1;
  return `Đăng ký bước ${step}/3 · ${Math.round(e.progress * 100)}%${redo}`;
}

export default function LiveScreen() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [session, setSession] = useState<Session | null>(loadSession);
  const [guest, setGuest] = useState(false);
  const [step, setStep] = useState<Step | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agent, setAgent] = useState<LiveAgent | null>(null);
  const [ended, setEnded] = useState(false); // trip ended: the summary is on screen, the camera is off
  const voice = useVietnameseVoice();

  useEffect(() => () => void agent?.stop(), [agent]);

  async function start() {
    if (!videoRef.current) return;
    setError(null);
    setEnded(false);
    try {
      setAgent(await LiveAgent.start(videoRef.current, guest ? null : session, setStep));
    } catch (err) {
      setError(cameraError(err));
      setStep(null);
    }
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
      {ready && <HudScreen source={agent} onTripEnded={() => setEnded(true)} onDone={stop} />}
      <SelfView videoRef={videoRef} agent={ended ? null : agent} onStop={stop} />
      {!ready && (
        <div className="live-setup font-hud text-hud-ink antialiased [color-scheme:dark]">
          {/* M64 (designs "Chạy thử trên trình duyệt · Thiết lập / Đang tải"): the pitch and the privacy
              promise on the left, the three steps (or the loading steps) on the right. */}
          <section className="live-intro">
            <div className="flex items-center gap-3">
              <span className="grid size-10 place-items-center rounded-hud-sm bg-hud-safe text-[#05210f]">
                <ShieldCheck aria-hidden className="size-6" strokeWidth={2.25} />
              </span>
              <span className="flex flex-col gap-0.5">
                <span className="text-[17px] font-semibold tracking-[0.12em]">DRIVERGUARD</span>
                <span className="text-[13px] text-hud-ink-3">Chạy thử bằng camera trên máy này</span>
              </span>
            </div>
            <div className="grid max-w-[540px] gap-4">
              <h1 className="m-0 text-[clamp(34px,4vw,52px)] leading-[1.08] font-semibold tracking-[-0.03em]">Giám sát tài xế ngay trên trình duyệt</h1>
              <p className="m-0 text-lg leading-relaxed text-hud-ink-2">
                Dùng webcam của bạn để nhận biết khi bạn buồn ngủ hoặc mất tập trung, và nhắc bạn bằng màu, chữ và âm thanh. Cuối chuyến có bản tổng kết.
              </p>
            </div>
            <div className="grid max-w-[540px] gap-3">
              <div className="dg-alert l0 flex gap-3.5 px-5 py-[18px]">
                <ShieldCheck aria-hidden className="mt-0.5 size-6 shrink-0 text-hud-safe" />
                <p className="m-0 text-[15px] leading-relaxed text-[#c9ddd0]">
                  <strong className="text-hud-ink">Hình ảnh không rời khỏi máy bạn.</strong> Mọi xử lý chạy trong trình duyệt này, không ghi ảnh ra đĩa.
                  Chỉ số liệu cảnh báo (mức, lý do, thời điểm) được gửi đi, và chỉ khi bạn đăng nhập.
                </p>
              </div>
              <a href="#/dashboard" className="text-sm text-hud-ink-3">
                Xem lại lịch sử cảnh báo trên Dashboard →
              </a>
            </div>
          </section>

          <section className="live-side">
            <div className="dg-card grid w-full max-w-[560px] gap-5 px-7 py-6">
              {step ? (
                <>
                  <span className="dg-card-title">
                    <b className="!text-xl !font-semibold">Đang khởi động</b>
                    <span>{guest || !session ? "Dùng thử · không lưu, không gửi gì đi" : `Lưu vào tài khoản ${session.username}`}</span>
                  </span>
                  <Progress step={step} />
                  <p className="m-0 text-[13px] leading-relaxed text-hud-ink-3">
                    Mọi thứ được tải về và chạy ngay trong trình duyệt này. Không có hình ảnh nào được gửi lên máy chủ.
                  </p>
                </>
              ) : (
                <>
                  <SetupStep n={1} title="Ai đang lái?">
                    {session && !guest ? (
                      <div className="dg-tile flex flex-wrap items-center gap-3 p-4">
                        <Check aria-hidden className="size-5 text-hud-safe" />
                        <span className="text-[15px]">
                          Đăng nhập: <strong>{session.username}</strong> · cảnh báo được lưu vào tài khoản
                        </span>
                        <button type="button" onClick={logout} className={`${BTN} dg-tile ml-auto min-h-10 text-hud-ink-2`}>
                          <LogOut aria-hidden className="size-4" /> Đổi tài khoản
                        </button>
                      </div>
                    ) : guest ? (
                      <div className="dg-tile flex flex-wrap items-center gap-3 p-4">
                        <span className="text-[15px]">Dùng thử: không lưu cảnh báo, không gửi gì đi.</span>
                        <button type="button" onClick={() => setGuest(false)} className={`${BTN} dg-tile ml-auto min-h-10 text-hud-ink-2`}>
                          Đăng nhập để lưu
                        </button>
                      </div>
                    ) : (
                      <LoginBox onLogin={setSession} onGuest={() => setGuest(true)} />
                    )}
                  </SetupStep>

                  <SetupStep n={2} title="Đăng ký khuôn mặt" note="khoảng 10 giây">
                    <ol className="m-0 grid list-none gap-2 p-0">
                      {["Nhìn thẳng vào camera", "Nhìn ra đường như khi lái", "Nhắm mắt đến khi nghe tiếng bíp"].map((t, i) => (
                        <li key={t} className="flex items-center gap-3 text-[15px] text-hud-ink-2">
                          <span className="dg-num grid size-7 shrink-0 place-items-center rounded-full bg-hud-system/15 text-[13px] font-semibold text-[#93c5fd]">
                            {i + 1}
                          </span>
                          {t}
                        </li>
                      ))}
                    </ol>
                    <p className="m-0 text-[13px] leading-relaxed text-hud-ink-3">
                      Lúc bắt đầu xe đang đỗ (0 km/h): hệ thống hướng dẫn bằng chữ và giọng nói, nhớ bật âm thanh. Đỗ hay đang lái là theo tốc độ từ
                      công cụ mô phỏng lái xe; chưa chạy công cụ thì xe được coi là đang đỗ. Nút “Đổi tài xế” để người lái mới đăng ký lại.
                    </p>
                  </SetupStep>

                  {voice === false && (
                    <p role="note" className="m-0 rounded-hud-sm border border-solid border-hud-caution/45 bg-hud-caution/10 p-3 text-[13px] leading-relaxed text-[#fde68a]">
                      {NO_VIETNAMESE_VOICE_TEXT}
                    </p>
                  )}

                  <SetupStep n={3} title="Bắt đầu">
                    <p className="m-0 text-[15px] text-hud-ink-2">
                      Đặt camera ngang mặt. Bấm “Kết thúc chuyến” khi xong để xem bản tổng kết. Nên dùng Chrome hoặc Edge trên máy tính.
                    </p>
                    <button
                      type="button"
                      onClick={start}
                      disabled={!session && !guest}
                      className="inline-flex min-h-14 w-full cursor-pointer items-center justify-center gap-2 rounded-hud-sm border-0 bg-[linear-gradient(180deg,#93c5fd_0%,#60a5fa_100%)] px-5 text-[17px] font-semibold text-[#0b1b33] disabled:cursor-not-allowed disabled:opacity-45"
                    >
                      <Camera aria-hidden className="size-5" /> Cho phép camera và bắt đầu
                    </button>
                    {!session && !guest && <p className="m-0 text-[13px] text-hud-ink-3">Đăng nhập hoặc chọn “Dùng thử” trước.</p>}
                  </SetupStep>
                </>
              )}

              {error && (
                <p role="alert" className="m-0 rounded-hud-sm bg-hud-danger/15 p-4 text-[15px] text-hud-ink ring-1 ring-hud-danger">
                  {error}
                </p>
              )}
            </div>
          </section>
        </div>
      )}
    </>
  );
}

function LoginBox({ onLogin, onGuest }: { onLogin: (s: Session) => void; onGuest: () => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await login(username.trim(), password);
      saveSession(s);
      onLogin(s);
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Sai tên đăng nhập hoặc mật khẩu" : String((err as Error).message));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} className="dg-tile grid gap-3 p-4">
      <div className="grid gap-3 sm:grid-cols-2">
        <input className={INPUT} placeholder="Tên đăng nhập" aria-label="Tên đăng nhập" autoComplete="username" value={username} onChange={(e) => setUsername(e.target.value)} required />
        <input className={INPUT} placeholder="Mật khẩu" aria-label="Mật khẩu" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
      </div>
      {error && (
        <p role="alert" className="m-0 text-hud-label text-hud-danger">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <button type="submit" disabled={busy} className={`${BTN} bg-[linear-gradient(180deg,#fff_0%,#d9d9d9_100%)] text-hud-bg`}>
          {busy ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
        <button type="button" onClick={onGuest} className={`${BTN} dg-tile text-hud-ink`}>
          Dùng thử không lưu
        </button>
      </div>
    </form>
  );
}

function SetupStep({ n, title, note, children }: { n: number; title: string; note?: string; children: React.ReactNode }) {
  return (
    <section className="grid gap-3">
      <h2 className="m-0 flex items-center gap-3 text-[17px] font-semibold">
        <span className="dg-num grid size-8 place-items-center rounded-full bg-white/8 text-sm">{n}</span>
        {title}
        {note && <span className="text-[13px] font-normal text-hud-ink-3">{note}</span>}
      </h2>
      {children}
    </section>
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

/** Small mirror of the driver's own camera (local only) with a plain status and a stop button.
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

  return (
    <div
      className={`fixed bottom-4 left-4 z-40 overflow-hidden rounded-hud-sm border border-solid border-white/15 bg-black/85 font-hud text-white shadow-[0_24px_48px_rgba(0,0,0,0.45)] backdrop-blur ${
        compact ? "w-auto" : tech ? "w-60" : "w-44"
      } ${agent ? "" : "pointer-events-none opacity-0"}`}
    >
      {/* Kept mounted (it holds the stream), only hidden at L3. Small (M64): it sits over the HUD. */}
      <video ref={videoRef} className={`aspect-[4/3] w-full -scale-x-100 object-cover ${compact ? "hidden" : "block"}`} muted playsInline />
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
                  data-perf={JSON.stringify({ perf: stats.perf, totals: stats.totals, startup: stats.startup, fps: stats.fps })}
                >
                  {perfLines(stats.perf)}
                </span>
              )}
              {stats?.enrollment && stats.enrollment.status !== "off" && (
                <span className="text-white/70">{enrollText(stats.enrollment)}</span>
              )}
              {stats?.lastError && <span className="break-all text-hud-caution">Lỗi gần nhất: {stats.lastError}</span>}
              {stats && stats.sent > 0 && <span className="text-white/70">Đã lưu {stats.sent} cảnh báo</span>}
            </>
          )}
          {stats?.sendError && <span className="text-hud-caution">{stats.sendError}</span>}
          <div className="flex items-center gap-1">
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
              title="Dừng camera"
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
