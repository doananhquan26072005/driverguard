// One login for every role (M60, design "Đăng nhập chung"): the backend returns the role, the app then
// opens that role's home page (nav.ts). The same page is the product's first page, #/live (`live`):
// there it also offers the try-out without an account, and a driver who is already logged in starts the
// trip from it. 13/10: the two cards "Không lưu ảnh khuôn mặt" / "Dữ liệu có hạn dùng" are gone (the
// user's choice); the guide (#/guide) still says how faces and data are kept.
import { type FormEvent, type ReactNode, useState } from "react";
import { ArrowRight, BookOpen, Camera, LogOut, ShieldCheck } from "lucide-react";
import { ApiError, login } from "../lib/api";
import { DEMO_DRIVER } from "../lib/demo";
import type { Session } from "../lib/types";

/** What the first page (#/live) adds to the login page. */
export interface LiveEntry {
  session: Session | null; // already logged in: no form, "Bắt đầu ca lái"
  onStart: () => void;
  onGuest: () => void; // "Dùng thử không lưu"
  onSwitch: () => void; // "Đổi tài khoản"
  note?: ReactNode; // e.g. the camera could not be opened
}

export default function Login({ onLogin, live }: { onLogin: (s: Session) => void; live?: LiveEntry }) {
  // The demo driver is filled in (lib/demo.ts): one press logs in.
  // Every login page, whichever way it was reached (first page, Dashboard, after logging out: 13/10).
  const demo = DEMO_DRIVER;
  const [username, setUsername] = useState(demo?.username ?? "");
  const [password, setPassword] = useState(demo?.password ?? "");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onLogin(await login(username.trim(), password));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Sai tên đăng nhập hoặc mật khẩu" : "Không đăng nhập được. Kiểm tra mạng rồi thử lại.");
    } finally {
      setBusy(false);
    }
  }

  const alt = (
    <div className="login-alt">
      {live?.note}
      {live ? (
        <button type="button" className="dg-card login-live" onClick={live.onGuest}>
          <span>
            <b>Dùng thử không lưu</b>
          </span>
          <ArrowRight aria-hidden size={20} />
        </button>
      ) : (
        <a className="dg-card login-live" href="#/live">
          <span>
            <b>Chạy thử bằng camera trên máy này</b>
            <span className="muted">Không cần tài khoản, không gửi gì đi</span>
          </span>
          <ArrowRight aria-hidden size={20} />
        </a>
      )}
    </div>
  );

  return (
    <div className="login-page">
      <section className="login-intro">
        <div className="brand">
          <span className="brand-mark" aria-hidden>
            <ShieldCheck size={22} strokeWidth={2.25} />
          </span>
          DriverGuard
        </div>
        <div className="login-pitch">
          <h1>Giúp mỗi chuyến đi của bạn an toàn hơn.</h1>
          <p>Thiết bị trong xe nhận biết buồn ngủ và mất tập trung ngay trên xe.</p>
        </div>
        {/* 13/10: a small link at the bottom, not a card (the user's choice). */}
        <a className="login-guide" href="#/guide" title="Các màn hình bạn sẽ gặp và việc nên làm. Không cần tài khoản.">
          <BookOpen aria-hidden size={18} />
          Hướng dẫn sử dụng
        </a>
      </section>

      <section className="login-side">
        {live?.session ? (
          <div className="login">
            <div>
              <h2>Bắt đầu ca lái</h2>
              <p className="muted">
                Đăng nhập: <b>{live.session.username}</b> · cảnh báo được lưu vào tài khoản
              </p>
            </div>
            <button type="button" className="primary big login-start" onClick={live.onStart}>
              <Camera aria-hidden size={20} /> Cho phép camera và bắt đầu
            </button>
            <div className="login-row">
              <a className="ghost" href="#/dashboard">
                Mở Dashboard
              </a>
              <button type="button" className="ghost" onClick={live.onSwitch}>
                <LogOut aria-hidden size={16} /> Đổi tài khoản
              </button>
            </div>
            {alt}
          </div>
        ) : (
          <form className="login" onSubmit={submit}>
            <div>
              <h2>Đăng nhập</h2>
              {demo && (
                <p className="form-note login-demo" role="note">
                  Đã điền sẵn tài khoản tài xế dùng thử <b>{demo.username}</b>: bấm <b>Đăng nhập</b> là vào{" "}
                  {live ? "màn hình giám sát" : "trang của tài xế"}.
                </p>
              )}
            </div>
            <label>
              Tên đăng nhập
              <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
            </label>
            <label>
              Mật khẩu
              <span className="password">
                <input
                  type={show ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                />
                <button type="button" className="link" onClick={() => setShow((v) => !v)} aria-pressed={show}>
                  {show ? "Ẩn" : "Hiện"}
                </button>
              </span>
            </label>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button type="submit" className="primary big" disabled={busy}>
              {busy ? "Đang đăng nhập…" : "Đăng nhập"}
            </button>
            <p className="muted small">Quên mật khẩu? Liên hệ quản trị viên của đội xe.</p>
            {alt}
          </form>
        )}
      </section>
    </div>
  );
}
