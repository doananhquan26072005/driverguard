// The demo accounts of the login page (13/10): the driver is filled in (a visitor presses "Đăng nhập" and
// the camera starts); a press on the username field also offers the engineer. Shown to everyone who opens
// the page: the driver only sees its own trips, but the engineer may change the fleet's thresholds, so
// leave it out of a build that strangers can open. The same accounts have to exist on each backend
// (python -m backend.manage create-user, docs/deploy-railway.md).
// Build-time switches: VITE_DEMO_USERNAME / VITE_DEMO_PASSWORD (driver; VITE_DEMO_USERNAME="" turns all
// of it off), VITE_DEMO_ENGINEER_USERNAME / VITE_DEMO_ENGINEER_PASSWORD (VITE_DEMO_ENGINEER_USERNAME=""
// keeps only the driver).
export interface DemoAccount {
  username: string;
  password: string;
  role: string; // shown next to the name
}

const env = import.meta.env;

function account(username: string | undefined, password: string | undefined, role: string): DemoAccount | null {
  return username ? { username, password: password ?? "", role } : null;
}

export const DEMO_DRIVER: DemoAccount | null = account(env.VITE_DEMO_USERNAME ?? "taixe_demo", env.VITE_DEMO_PASSWORD ?? "demo12345", "Tài xế");

/** Every demo account, the driver first (the one filled in). Empty when the demo is off. */
export const DEMO_ACCOUNTS: DemoAccount[] = DEMO_DRIVER
  ? [
      DEMO_DRIVER,
      account(env.VITE_DEMO_ENGINEER_USERNAME ?? "kysu_demo", env.VITE_DEMO_ENGINEER_PASSWORD ?? "kysu12345", "Kỹ sư"),
    ].filter((a): a is DemoAccount => a != null)
  : [];
