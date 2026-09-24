import { type FormEvent, useState } from "react";
import { ApiError, login } from "../lib/api";
import type { Session } from "../lib/types";

export default function Login({ onLogin }: { onLogin: (s: Session) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

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

  return (
    <div className="login-page">
      <form className="card login" onSubmit={submit}>
        <h1>DriverGuard</h1>
        <p className="muted">Đăng nhập dành cho quản lý đội xe, kỹ sư và tài xế</p>
        <label>
          Tên đăng nhập
          <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" required />
        </label>
        <label>
          Mật khẩu
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Đang đăng nhập…" : "Đăng nhập"}
        </button>
        <a className="muted small" href="#/hud">
          Mở HUD trong xe →
        </a>
      </form>
    </div>
  );
}
