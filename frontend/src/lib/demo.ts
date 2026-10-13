// The driver account the first page (#/live) fills in (13/10): a visitor presses "Đăng nhập" and the
// camera starts. A demo account, shown to everyone who opens the page: it only sees its own trips. The
// same account has to exist on each backend (python -m backend.manage create-user, docs/deploy-railway.md).
// VITE_DEMO_USERNAME / VITE_DEMO_PASSWORD change it at build time; VITE_DEMO_USERNAME="" turns it off.
export const DEMO_DRIVER: { username: string; password: string } | null = (() => {
  const username = import.meta.env.VITE_DEMO_USERNAME ?? "taixe_demo";
  const password = import.meta.env.VITE_DEMO_PASSWORD ?? "demo12345";
  return username ? { username, password } : null;
})();
