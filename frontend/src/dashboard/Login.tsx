// One login for every role (M60, design "Đăng nhập chung"): the backend returns the role, the app then
// opens that role's home page (nav.ts). The same page is the product's first page, #/live (`live`):
// there it also offers the try-out without an account, and a driver who is already logged in starts the
// trip from it. 13/10: the two cards "Không lưu ảnh khuôn mặt" / "Dữ liệu có hạn dùng" are gone (the
// user's choice); the guide (#/guide) still says how faces and data are kept.
// 14/10: the first column follows option 6 of the background mock-up: a green glow, the shield mascot
// as the logo, the thinking mascot on the guide link, and three strengths with an icon and a short line.
import { type FormEvent, type ReactNode, useState } from "react";
import { ArrowRight, Camera, LogOut } from "lucide-react";
import { BrandMark, BrandName } from "../brand/Brand";
import mascotThink from "../assets/mascot-think.png";
import { ApiError, login } from "../lib/api";
import { DEMO_ACCOUNTS, DEMO_DRIVER, type DemoAccount } from "../lib/demo";
import type { Session } from "../lib/types";

/** What the first page (#/live) adds to the login page. */
export interface LiveEntry {
  session: Session | null; // already logged in: no form, "Bắt đầu ca lái"
  onStart: () => void;
  onGuest: () => void; // "Dùng thử không lưu"
  onSwitch: () => void; // "Đổi tài khoản"
  note?: ReactNode; // e.g. the camera could not be opened
}

// The three strengths under the pitch (option 6): icon paths (24 × 24, stroked), title, one short line.
const FEATURES: { icon: ReactNode; title: string; line: string }[] = [
  {
    icon: (
      <>
        <rect x="6" y="6" width="12" height="12" rx="2" />
        <rect x="9.5" y="9.5" width="5" height="5" rx="1" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
      </>
    ),
    title: "Xử lý ngay trên xe",
    line: "Không cần mạng, phản hồi tức thì",
  },
  {
    icon: (
      <>
        <path d="M4 8V6a2 2 0 0 1 2-2h2M16 4h2a2 2 0 0 1 2 2v2M20 16v2a2 2 0 0 1-2 2h-2M8 20H6a2 2 0 0 1-2-2v-2" />
        <path d="M9 15c.8.6 1.8 1 3 1s2.2-.4 3-1M9 10h.01M15 10h.01" />
        <path d="M3 3l18 18" />
      </>
    ),
    title: "Không lưu ảnh khuôn mặt",
    line: "Chỉ gửi số liệu, ảnh không rời khỏi máy",
  },
  {
    icon: <path d="M5 20v-3M10 20v-7M15 20v-11M20 20V5" />,
    title: "Cảnh báo theo 4 mức",
    line: "Từ nhắc nhẹ đến báo động, hạn chế báo nhầm",
  },
];

export default function Login({ onLogin, live }: { onLogin: (s: Session) => void; live?: LiveEntry }) {
  // The demo driver is filled in (lib/demo.ts): one press logs in.
  // Every login page, whichever way it was reached (first page, Dashboard, after logging out: 13/10).
  const demo = DEMO_DRIVER;
  const [username, setUsername] = useState(demo?.username ?? "");
  const [password, setPassword] = useState(demo?.password ?? "");
  const [show, setShow] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // 13/10: a press on the username field lists the demo accounts (driver, engineer); one tap fills both fields.
  const [picking, setPicking] = useState(false);
  const pick = (a: DemoAccount) => {
    setUsername(a.username);
    setPassword(a.password);
    setPicking(false);
  };
  const picked = DEMO_ACCOUNTS.find((a) => a.username === username.trim());

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
        // Straight into the try-out (#/live?guest), not the first page's login again (13/10).
        <a className="dg-card login-live" href="#/live?guest">
          <span>
            <b>Dùng thử không lưu</b>
          </span>
          <ArrowRight aria-hidden size={20} />
        </a>
      )}
    </div>
  );

  return (
    <div className="login-page">
      <section className="login-intro">
        <div className="brand login-brand">
          <BrandMark />
          <span>
            <BrandName />
          </span>
        </div>
        <div className="login-pitch">
          <h1>Giúp mỗi chuyến đi của bạn an toàn hơn.</h1>
          <p>Thiết bị nhận biết buồn ngủ và mất tập trung.</p>
          <ul className="login-features">
            {FEATURES.map((f) => (
              <li key={f.title}>
                <i aria-hidden>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
                    {f.icon}
                  </svg>
                </i>
                <span className="login-feature-title">{f.title}</span>
                <span className="login-feature-line">{f.line}</span>
              </li>
            ))}
          </ul>
        </div>
        {/* 13/10: a small link at the bottom, not a card (the user's choice). 14/10: no "Quyền riêng tư"
            link here (the user's choice); #/privacy is still reached from #/guide. */}
        <a className="login-guide login-guide-mascot" href="#/guide" title="Các màn hình bạn sẽ gặp và việc nên làm. Không cần tài khoản.">
          <img src={mascotThink} alt="" />
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
              {/* 13/10: no note about the filled-in demo account (the user's choice); the fields say it. */}
              <h2>Đăng nhập</h2>
            </div>
            <label className="login-user">
              Tên đăng nhập
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                onFocus={() => setPicking(DEMO_ACCOUNTS.length > 1)}
                onBlur={() => setPicking(false)}
                autoComplete="username"
                aria-controls={picking ? "demo-accounts" : undefined}
                aria-expanded={DEMO_ACCOUNTS.length > 1 ? picking : undefined}
                required
              />
              {picking && (
                <ul id="demo-accounts" role="listbox" aria-label="Tài khoản dùng thử" className="login-accounts">
                  {DEMO_ACCOUNTS.map((a) => (
                    <li
                      key={a.username}
                      role="option"
                      aria-selected={picked?.username === a.username}
                      // mousedown, not click: the field's blur would close the list before the click lands
                      onMouseDown={(e) => {
                        e.preventDefault();
                        pick(a);
                      }}
                    >
                      <span>{a.username}</span>
                      <span className="muted">{a.role}</span>
                    </li>
                  ))}
                </ul>
              )}
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
