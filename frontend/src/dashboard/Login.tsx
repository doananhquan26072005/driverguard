// One login for every role (M60, design "Đăng nhập chung"): the backend returns the role, the app then
// opens that role's home page (nav.ts). The retention days come from /api/v1/policy, never hard-coded.
import { type FormEvent, useEffect, useState } from "react";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { ApiError, getPolicy, login } from "../lib/api";
import type { Session } from "../lib/types";

export default function Login({ onLogin }: { onLogin: (s: Session) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [days, setDays] = useState<{ events: number; summaries: number } | null>(null);

  useEffect(() => {
    getPolicy()
      .then((p) => setDays({ events: p.retention_events_days, summaries: p.retention_summaries_days }))
      .catch(() => undefined); // backend down: the card says nothing about days rather than guessing
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      onLogin(await login(username.trim(), password));
    } catch (err) {
      setError(err instanceof ApiError && err.status === 401 ? "Sai tên đăng nhập hoặc mật khẩu" : String((err as Error).message));
    } finally {
      setBusy(false);
    }
  }

  const keep = (n: number) => (n > 0 ? `sau ${n} ngày` : "khi quản trị viên xoá");

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
          <h1>Mỗi chuyến đi an toàn hơn, không cần lưu một tấm ảnh nào.</h1>
          <p>Thiết bị trong xe nhận biết buồn ngủ và mất tập trung ngay trên xe. Máy chủ chỉ nhận số liệu cảnh báo: mức, lý do, thời điểm.</p>
        </div>
        <ul className="login-facts">
          <li className="dg-card">
            <b>Không lưu ảnh khuôn mặt</b>
            <span>Hình ảnh camera chỉ được xử lý trong xe.</span>
          </li>
          <li className="dg-card">
            <b>Dữ liệu có hạn dùng</b>
            <span>
              {days
                ? `Cảnh báo tự xoá ${keep(days.events)}, tổng kết chuyến ${keep(days.summaries)}.`
                : "Cảnh báo và tổng kết chuyến tự xoá theo thời hạn của đội xe."}
            </span>
          </li>
        </ul>
      </section>

      <section className="login-side">
        <form className="login" onSubmit={submit}>
          <div>
            <h2>Đăng nhập</h2>
            <p className="muted">Dùng chung cho tài xế, quản lý đội xe, kỹ sư và quản trị. Bạn sẽ vào đúng trang của vai trò mình.</p>
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
          <div className="login-alt">
            <a className="dg-card login-live" href="#/live">
              <span>
                <b>Chạy thử bằng camera trên máy này</b>
                <span className="muted">Không cần tài khoản, không gửi gì đi</span>
              </span>
              <ArrowRight aria-hidden size={20} />
            </a>
            <p className="muted small">
              Màn hình trong xe (<a href="#/hud">HUD</a>) không cần đăng nhập: thiết bị đã gắn sẵn với xe.
            </p>
          </div>
        </form>
      </section>
    </div>
  );
}
