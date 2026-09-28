// #/live: DriverGuard on the visitor's own camera, everything computed in this browser.
// Setup (who is driving, CAN scenario, privacy) -> loading steps -> the in-car HUD fed by
// LiveAgent, with a small self-view so the driver can place the camera.
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Camera, Check, LoaderCircle, LogOut, ShieldCheck, Square } from "lucide-react";
import HudScreen from "../hud/HudScreen";
import { ApiError, loadSession, login, saveSession } from "../lib/api";
import type { Session } from "../lib/types";
import { LiveAgent, SCENARIOS, STEPS, type LiveStats, type Scenario, type Step } from "./agent";

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

export default function LiveScreen() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [session, setSession] = useState<Session | null>(loadSession);
  const [guest, setGuest] = useState(false);
  const [scenario, setScenario] = useState<Scenario>("highway_night");
  const [step, setStep] = useState<Step | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [agent, setAgent] = useState<LiveAgent | null>(null);

  useEffect(() => () => void agent?.stop(), [agent]);

  async function start() {
    if (!videoRef.current) return;
    setError(null);
    try {
      setAgent(await LiveAgent.start(videoRef.current, scenario, guest ? null : session, setStep));
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
      {ready && <HudScreen source={agent} />}
      <SelfView videoRef={videoRef} agent={agent} onStop={stop} />
      {!ready && (
        <div className="min-h-dvh bg-hud-bg font-hud text-hud-ink antialiased [color-scheme:dark]">
          <main className="mx-auto grid max-w-2xl gap-6 px-4 py-8 sm:py-12">
            <header className="grid gap-2">
              <p className="text-hud-label font-bold tracking-tight text-hud-system">DriverGuard</p>
              <h1 className="m-0 text-hud-title font-bold">Giám sát tài xế ngay trên trình duyệt</h1>
              <p className="m-0 text-hud-body text-hud-ink-2">
                Dùng webcam của bạn để phát hiện buồn ngủ và mất tập trung, cảnh báo theo 4 mức L0–L3.
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
                  <h2 className="m-0 text-hud-body font-semibold">2. Tình huống xe (tốc độ giả lập)</h2>
                  <div role="radiogroup" className="grid gap-2">
                    {(Object.keys(SCENARIOS) as Scenario[]).map((s) => (
                      <label
                        key={s}
                        className={`flex min-h-12 cursor-pointer items-center gap-3 rounded-hud-sm px-4 py-2 ring-1 ${
                          scenario === s ? "bg-hud-raised ring-hud-system" : "bg-hud-surface ring-hud-line"
                        }`}
                      >
                        <input type="radio" name="scenario" checked={scenario === s} onChange={() => setScenario(s)} className="size-4 accent-[var(--color-hud-system)]" />
                        <span className="text-hud-label">{SCENARIOS[s]}</span>
                      </label>
                    ))}
                  </div>
                </section>

                <section className="grid gap-3">
                  <h2 className="m-0 text-hud-body font-semibold">3. Bắt đầu</h2>
                  <p className="m-0 text-hud-label text-hud-ink-2">
                    Đặt camera ngang mặt, nhìn thẳng 10–20 giây đầu để hệ thống học mắt và tư thế đầu của bạn. Nên dùng
                    Chrome hoặc Edge trên máy tính.
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
  const current = step === "ready" ? order.length : order.indexOf(step);
  return (
    <ol className="m-0 grid list-none gap-2 p-0" aria-live="polite">
      {order.map((s, i) => (
        <li key={s} className="flex min-h-12 items-center gap-3 rounded-hud-sm bg-hud-surface px-4 ring-1 ring-hud-line">
          {i < current ? (
            <Check aria-hidden className="size-5 text-hud-safe" />
          ) : i === current ? (
            <LoaderCircle aria-hidden className="size-5 animate-spin text-hud-system" />
          ) : (
            <span aria-hidden className="size-5" />
          )}
          <span className={`text-hud-label ${i <= current ? "text-hud-ink" : "text-hud-ink-3"}`}>{STEPS[s]}</span>
        </li>
      ))}
    </ol>
  );
}

/** Small mirror of the driver's own camera (local only) with the live measurements and a stop button.
 * At L3 it shrinks to the stop button: the HUD then shows nothing but the stop message. */
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
          <span>
            {m?.face ? "Có mặt" : "Không thấy mặt"} · EAR {fmt(m?.ear)} · {fmt(stats?.fps, 0)} FPS
          </span>
          <span className="text-white/70">
            Yaw {fmt(m?.yaw, 0)}° · Pitch {fmt(m?.pitch, 0)}° · ĐT{" "}
            {stats?.phoneOn ? `${m?.phone ? "có" : "không"} (${fmt(stats.yoloMs, 0)} ms)` : "tắt"}
          </span>
          {stats?.sendError ? (
            <span className="text-hud-caution">{stats.sendError}</span>
          ) : (
            stats && stats.sent > 0 && <span className="text-white/70">Đã lưu {stats.sent} cảnh báo</span>
          )}
          <button type="button" onClick={onStop} className="mt-1 inline-flex min-h-9 items-center justify-center gap-1 rounded-full border-0 bg-white/15 text-[13px] font-semibold text-white">
            <Square aria-hidden className="size-3.5" /> Dừng camera
          </button>
        </div>
      )}
    </div>
  );
}
