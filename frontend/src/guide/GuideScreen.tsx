// #/guide (M102): the user guide ("Hướng dẫn sử dụng"), opened from the login page. No login, no camera, no backend: the screens the product can
// show, each drawn by the real HUD on fixed numbers (ScreenFrame.tsx), with what it means and what to
// do next to it (guideModel.ts). Laid out as an app, not a page: one window-high shell that never
// scrolls, a bar of sections on top (welcome, the five chapters, the web pages), one screen at a time
// and "Trước" / "Tiếp" at the bottom. #/guide/<step> opens one step, so a screen can be linked. Moving
// inside the guide replaces the address instead of adding to the history: "back" leaves it in one press.
import { useEffect, useRef, useState } from "react";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { BrandMark } from "../brand/Brand";
import type { Role } from "../lib/types";
import { GUIDE, GUIDE_STEPS, guideHref, locate, ROLE_PAGES, stepFromHash, viewFromHash, WEB_KEY } from "./guideModel";
import ScreenFrame from "./ScreenFrame";

export default function GuideScreen() {
  const [hash, setHash] = useState(() => window.location.hash);
  const [role, setRole] = useState<Role>("driver");
  const view = viewFromHash(hash);
  const step = stepFromHash(hash);
  const { chapter, index } = locate(step.key);
  const prev = GUIDE_STEPS[index - 1];
  const next = GUIDE_STEPS[index + 1];
  const pages = ROLE_PAGES.find((r) => r.role === role) ?? ROLE_PAGES[0];

  const go = (key?: string) => {
    window.history.replaceState(null, "", guideHref(key));
    setHash(window.location.hash);
  };

  // A link to another step (typed, or followed from elsewhere in the app) while the guide is open.
  useEffect(() => {
    const onHash = () => setHash(window.location.hash);
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  // The bar of sections scrolls sideways on a phone: keep the open one in sight.
  const tabs = useRef<HTMLElement>(null);
  const section = view === "step" ? chapter.title : view;
  useEffect(() => {
    tabs.current?.querySelector('[aria-current="page"]')?.scrollIntoView?.({ inline: "center", block: "nearest" });
  }, [section]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.altKey || e.ctrlKey || e.metaKey || view !== "step") return;
      if (e.key === "ArrowRight" && next) go(next.key);
      if (e.key === "ArrowLeft" && prev) go(prev.key);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  return (
    <div className="guide">
      <header className="guide-bar">
        <a className="guide-back" href="#/live" aria-label="Về trang đăng nhập">
          <ArrowLeft aria-hidden size={20} />
        </a>
        <BrandMark />
        <h1>Hướng dẫn sử dụng</h1>
        <a className="ghost" href="#/privacy">
          Quyền riêng tư
        </a>
      </header>

      <nav ref={tabs} className="guide-tabs" aria-label="Các phần của hướng dẫn">
        <button type="button" className="guide-tab" aria-current={view === "intro" ? "page" : undefined} onClick={() => go()}>
          Giới thiệu
        </button>
        {GUIDE.map((c) => (
          <button
            key={c.title}
            type="button"
            className="guide-tab"
            aria-current={view === "step" && c === chapter ? "page" : undefined}
            onClick={() => go(c.steps[0].key)}
          >
            {c.title}
          </button>
        ))}
        <button type="button" className="guide-tab" aria-current={view === "web" ? "page" : undefined} onClick={() => go(WEB_KEY)}>
          Trang web
        </button>
      </nav>

      {view === "intro" && (
        <main className="guide-main guide-intro">
          <div className="guide-intro-text">
            <h2>Những màn hình bạn sẽ gặp, và việc nên làm</h2>
            <p>
              DriverGuard nhìn khuôn mặt người lái qua camera trong xe và nhắc khi thấy dấu hiệu buồn ngủ hoặc mất tập trung. Mỗi màn hình trong
              hướng dẫn này kèm ý nghĩa và việc nên làm.
            </p>
            <button type="button" className="primary big" onClick={() => go(GUIDE_STEPS[0].key)}>
              Bắt đầu <ArrowRight aria-hidden size={18} />
            </button>
          </div>
          <ul className="guide-facts">
            <li className="dg-card">
              <b>Không lưu ảnh khuôn mặt</b>
              <span>
                Hình camera chỉ được xử lý ngay trong xe. Máy chủ chỉ nhận con số: mức, lý do, thời điểm. <a href="#/privacy">Quyền riêng tư</a>
              </span>
            </li>
            <li className="dg-card">
              <b>Nghe là đủ</b>
              <span>Mọi cảnh báo đều có tiếng và lời nói. Khi lái, bạn không cần nhìn màn hình.</span>
            </li>
            <li className="dg-card">
              <b>Cảnh báo có thể nhầm</b>
              <span>Hệ thống chỉ hỗ trợ, không thay bạn. Thấy cảnh báo sai thì chạm “Cảnh báo nhầm?” để hệ thống ghi nhận.</span>
            </li>
          </ul>
        </main>
      )}

      {view === "step" && (
        <>
          <main className="guide-main guide-stage" aria-label="Các màn hình">
            <div className="guide-view">
              <ScreenFrame scenario={step.scenario} label={step.title} />
              <p className="muted small guide-caption">Hình minh hoạ với số liệu mẫu. Màn hình trong xe trông đúng như thế này.</p>
            </div>
            <article className="guide-explain dg-card" aria-live="polite">
              <header>
                <span className="muted small">
                  {chapter.title} · {index + 1} / {GUIDE_STEPS.length}
                </span>
                <h2>
                  <i className={`guide-dot ${step.tone}`} aria-hidden />
                  {step.title}
                </h2>
              </header>
              <div>
                <h3>Màn hình này nghĩa là gì</h3>
                <p>{step.means}</p>
              </div>
              <div>
                <h3>Bạn nên làm gì</h3>
                <p>{step.todo}</p>
              </div>
            </article>
          </main>
          <footer className="guide-nav">
            <button type="button" className="ghost" aria-label="Trước" disabled={!prev} onClick={() => prev && go(prev.key)}>
              <ArrowLeft aria-hidden size={18} /> <span>Trước</span>
            </button>
            <nav className="guide-steps" aria-label={`Các màn hình của phần ${chapter.title}`}>
              {chapter.steps.map((s) => (
                <button
                  key={s.key}
                  type="button"
                  className="guide-item"
                  title={s.title}
                  aria-label={s.title}
                  aria-current={s.key === step.key ? "step" : undefined}
                  onClick={() => go(s.key)}
                >
                  <i className={`guide-dot ${s.tone}`} aria-hidden />
                </button>
              ))}
            </nav>
            <button type="button" className="primary" aria-label="Tiếp" disabled={!next} onClick={() => next && go(next.key)}>
              <span>Tiếp</span> <ArrowRight aria-hidden size={18} />
            </button>
          </footer>
        </>
      )}

      {view === "web" && (
        <main className="guide-main guide-web">
          <header>
            <h2>Trang web sau khi đăng nhập</h2>
            <p className="muted">Mọi người dùng chung một trang đăng nhập. Vai trò của tài khoản quyết định bạn thấy những trang nào.</p>
          </header>
          <div className="guide-roles" role="tablist" aria-label="Vai trò">
            {ROLE_PAGES.map((r) => (
              <button key={r.role} type="button" role="tab" className="guide-tab" aria-selected={r.role === role} onClick={() => setRole(r.role)}>
                {r.name}
              </button>
            ))}
          </div>
          <section className="guide-role" role="tabpanel" aria-label={pages.name}>
            <p className="muted">{pages.intro}</p>
            <dl>
              {pages.pages.map((p) => (
                <div key={p.page} className="dg-card">
                  <dt>{p.label}</dt>
                  <dd className="muted">{p.lead}</dd>
                </div>
              ))}
            </dl>
          </section>
        </main>
      )}
    </div>
  );
}
