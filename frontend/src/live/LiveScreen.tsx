// #/live: DriverGuard on the visitor's own camera, everything computed in this browser.
// Setup (who is driving, face enrollment, privacy) -> loading steps -> the in-car HUD fed by
// LiveAgent, with a small self-view so the driver can place the camera.
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Camera, Check, Gauge, LoaderCircle, LogOut, ShieldCheck, Square } from "lucide-react";
import HudScreen from "../hud/HudScreen";
import { ApiError, loadSession, login, saveSession } from "../lib/api";
import { perfDetail, perfLines } from "../lib/labels";
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
        <div className="min-h-dvh bg-hud-bg font-hud text-hud-ink antialiased [color-scheme:dark]">
          <main className="mx-auto grid max-w-2xl gap-6 px-4 py-8 sm:py-12">
            <header className="grid gap-2">
              <p className="text-hud-label font-bold tracking-tight text-hud-system">DriverGuard</p>
              <h1 className="m-0 text-hud-title font-bold">Giám sát tài xế ngay trên trình duyệt</h1>
              <p className="m-0 text-hud-body text-hud-ink-2">
                Dùng webcam của bạn để nhận biết khi bạn buồn ngủ hoặc mất tập trung, và nhắc bạn bằng màu, chữ và
                âm thanh. Cuối chuyến có bản tổng kết.
              </p>
            </header>

            <section className="flex gap-3 rounded-hud-sm bg-hud-surface p-4 ring-1 ring-hud-line">
              <ShieldCheck aria-hidden className="mt-0.5 size-6 shrink-0 text-hud-safe" />
              <p className="m-0 text-hud-label text-hud-ink-2">
                <strong className="text-hud-ink">Hình ảnh không rời khỏi máy bạn.</strong> Mọi xử lý chạy trong
                trình duyệt này, không ghi ảnh ra đĩa. Chỉ số liệu cảnh báo (mức, lý do, thời điểm) được gửi đi, và chỉ
                khi bạn đăng nhập.
              </p>
            </section>

            {step ? (
              <Progress step={step} />
            ) : (
              <>
                <section className="grid gap-3">
                  <h2 className="m-0 text-hud-body font-semibold">1. Ai đang lái?</h2>
                  {session && !guest ? (
                    <div className="flex flex-wrap items-center gap-3 rounded-hud-sm bg-hud-surface p-4 ring-1 ring-hud-line">
                      <Check aria-hidden className="size-5 text-hud-safe" />
                      <span className="text-hud-label">
                        Đăng nhập: <strong>{session.username}</strong> · cảnh báo được lưu vào tài khoản
                      </span>
                      <button type="button" onClick={logout} className={`${BTN} ml-auto min-h-10 bg-hud-raised text-hud-ink-2 ring-1 ring-hud-line`}>
                        <LogOut aria-hidden className="size-4" /> Đổi tài khoản
                      </button>
                    </div>
                  ) : guest ? (
                    <div className="flex flex-wrap items-center gap-3 rounded-hud-sm bg-hud-surface p-4 ring-1 ring-hud-line">
                      <span className="text-hud-label">Dùng thử: không lưu cảnh báo, không gửi gì đi.</span>
                      <button type="button" onClick={() => setGuest(false)} className={`${BTN} ml-auto min-h-10 bg-hud-raised text-hud-ink-2 ring-1 ring-hud-line`}>
                        Đăng nhập để lưu
                      </button>
                    </div>
                  ) : (
                    <LoginBox onLogin={setSession} onGuest={() => setGuest(true)} />
                  )}
                </section>

                <section className="grid gap-3">
                  <h2 className="m-0 text-hud-body font-semibold">2. Đăng ký khuôn mặt (khoảng 10 giây)</h2>
                  <ol className="m-0 grid gap-2 rounded-hud-sm bg-hud-surface p-4 pl-9 text-hud-label text-hud-ink-2 ring-1 ring-hud-line">
                    <li>Nhìn thẳng vào camera.</li>
                    <li>Nhìn ra đường phía trước như khi lái.</li>
                    <li>Nhắm mắt đến khi nghe tiếng bíp.</li>
                  </ol>
                  <p className="m-0 text-hud-label text-hud-ink-3">
                    Lúc bắt đầu xe đang đỗ (0 km/h): hệ thống hướng dẫn từng bước bằng chữ và giọng nói (nhớ bật âm
                    thanh). Đỗ hay đang lái là theo tốc độ xe, lấy từ công cụ mô phỏng lái xe trên máy này; chưa chạy công
                    cụ thì xe được coi là đang đỗ. Nút “Đổi tài xế” để người lái mới đăng ký lại.
                  </p>
                </section>

                <section className="grid gap-3">
                  <h2 className="m-0 text-hud-body font-semibold">3. Bắt đầu</h2>
                  <p className="m-0 text-hud-label text-hud-ink-2">
                    Đặt camera ngang mặt. Bấm “Kết thúc chuyến” khi xong để xem bản tổng kết. Nên dùng Chrome hoặc Edge
                    trên máy tính.
                  </p>
                  <button
                    type="button"
                    onClick={start}
                    disabled={!session && !guest}
                    className={`${BTN} w-full bg-hud-system text-hud-on-warning sm:w-fit`}
                  >
                    <Camera aria-hidden className="size-5" /> Cho phép camera và bắt đầu
                  </button>
                  {!session && !guest && <p className="m-0 text-hud-label text-hud-ink-3">Đăng nhập hoặc chọn “Dùng thử” trước.</p>}
                </section>
              </>
            )}

            {error && (
              <p role="alert" className="m-0 rounded-hud-sm bg-hud-danger/15 p-4 text-hud-label text-hud-ink ring-1 ring-hud-danger">
                {error}
              </p>
            )}
            <a href="#/dashboard" className="text-hud-label text-hud-ink-3">
              Xem lại lịch sử cảnh báo trên Dashboard →
            </a>
          </main>
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
    <form onSubmit={submit} className="grid gap-3 rounded-hud-sm bg-hud-surface p-4 ring-1 ring-hud-line">
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
        <button type="submit" disabled={busy} className={`${BTN} bg-hud-ink text-hud-bg`}>
          {busy ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
        <button type="button" onClick={onGuest} className={`${BTN} bg-hud-raised text-hud-ink ring-1 ring-hud-line`}>
          Dùng thử không lưu
        </button>
      </div>
    </form>
  );
}

function Progress({ step }: { step: Step }) {
  const order = Object.keys(STEPS) as (keyof typeof STEPS)[];
  const shown = step;
  const current = shown.step === "ready" ? order.length : order.indexOf(shown.step);
  return (
    <ol className="m-0 grid list-none gap-2 p-0" aria-live="polite">
      {order.map((s, i) => (
        <li key={s} className="grid min-h-12 gap-2 rounded-hud-sm bg-hud-surface px-4 py-3 ring-1 ring-hud-line">
          <div className="flex items-center gap-3">
            {i < current ? (
              <Check aria-hidden className="size-5 text-hud-safe" />
            ) : i === current ? (
              <LoaderCircle aria-hidden className="size-5 animate-spin text-hud-system" />
            ) : (
              <span aria-hidden className="size-5" />
            )}
            <span className={`text-hud-label ${i <= current ? "text-hud-ink" : "text-hud-ink-3"}`}>{STEPS[s]}</span>
          </div>
          {s === "prepare" && i === current && (
            <div role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(shown.progress * 100)} className="h-2 overflow-hidden rounded-full bg-hud-raised">
              <div className="h-full origin-left bg-hud-system transition-transform duration-300" style={{ transform: `scaleX(${Math.max(shown.progress, 0.05)})` }} />
            </div>
          )}
        </li>
      ))}
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
      className={`fixed bottom-4 left-4 z-40 overflow-hidden rounded-hud-sm bg-black font-hud text-white shadow-2xl ring-1 ring-white/20 ${
        compact ? "w-auto bg-black/40" : "w-44 sm:w-56"
      } ${agent ? "" : "pointer-events-none opacity-0"}`}
    >
      {/* Kept mounted (it holds the stream), only hidden at L3. */}
      <video ref={videoRef} className={`aspect-[4/3] w-full -scale-x-100 object-cover ${compact ? "hidden" : "block"}`} muted playsInline />
      {agent && compact && (
        <button type="button" onClick={onStop} className="inline-flex min-h-10 items-center gap-1 rounded-full border-0 bg-transparent px-4 text-[13px] font-semibold text-white">
          <Square aria-hidden className="size-3.5" /> Dừng camera
        </button>
      )}
      {agent && !compact && (
        <div className="grid gap-1 p-2 text-[13px] leading-tight tabular-nums">
          <span className={m?.face ? "" : "text-hud-caution"}>
            {m?.face ? "Đang theo dõi" : "Không thấy mặt, hãy chỉnh camera"}
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
                <span className="whitespace-pre-line text-white/70" title={perfDetail(stats.perf)}>
                  {perfLines(stats.perf)}
                </span>
              )}
              {stats?.enrollment && stats.enrollment.status !== "off" && (
                <span className="text-white/70">{enrollText(stats.enrollment)}</span>
              )}
              {stats?.lastError && <span className="break-all text-hud-caution">Lỗi gần nhất: {stats.lastError}</span>}
            </>
          )}
          <a
            href={`#/drive?code=${agent.driveCode}`}
            target="_blank"
            rel="noopener"
            className="mt-1 inline-flex min-h-9 items-center justify-center gap-1 rounded-full bg-hud-system/20 px-2 text-[13px] font-semibold text-white no-underline"
          >
            <Gauge aria-hidden className="size-3.5" /> Điều khiển xe · mã {agent.driveCode}
          </a>
          {stats?.sendError ? (
            <span className="text-hud-caution">{stats.sendError}</span>
          ) : (
            tech && stats && stats.sent > 0 && <span className="text-white/70">Đã lưu {stats.sent} cảnh báo</span>
          )}
          <button type="button" onClick={toggleTech} aria-pressed={tech} className="mt-1 min-h-8 rounded-full border-0 bg-transparent text-[12px] text-white/60 underline">
            {tech ? "Ẩn chi tiết kỹ thuật" : "Chi tiết kỹ thuật"}
          </button>
          <button type="button" onClick={onStop} className="mt-1 inline-flex min-h-9 items-center justify-center gap-1 rounded-full border-0 bg-white/15 text-[13px] font-semibold text-white">
            <Square aria-hidden className="size-3.5" /> Dừng camera
          </button>
        </div>
      )}
    </div>
  );
}
