// Web pages per role (M60, design "Sau đăng nhập: mỗi vai trò một trang chủ"): one login form, then each
// role lands on its own home page and sees only its own menu. Pages are hash routes #/dashboard/<page>,
// so a page can be linked and survives a reload. Pure, unit-tested in nav.test.ts. Which data a role
// may read is still decided by the backend (require_roles); the menu only hides what would be refused.
import type { Role } from "../lib/types";

export type PageKey =
  | "overview" // driver / manager home (M61 / M62)
  | "trips" // the driver's own trips (trip reports, scoped by the backend)
  | "alerts" // the driver's own alerts (event log, scoped by the backend)
  | "mydata" // the driver's data: download, delete request, who looked at it (M41 / M48)
  | "fleet"
  | "reports"
  | "events"
  | "timeline"
  | "thresholds"
  | "accounts" // admin (M63)
  | "devices" // admin (M63)
  | "access"; // admin: access log + deletion requests (M41 / M48)

export interface NavItem {
  page: PageKey;
  label: string;
}
export interface NavSection {
  title: string | null;
  items: NavItem[];
}

const ENGINEER: NavItem[] = [
  { page: "thresholds", label: "Ngưỡng và báo sai" },
  { page: "events", label: "Nhật ký sự kiện" },
  { page: "timeline", label: "Timeline mệt mỏi" },
  { page: "fleet", label: "Đội xe" },
  { page: "reports", label: "Báo cáo chuyến" },
];

export const NAV: Record<Role, NavSection[]> = {
  driver: [
    {
      title: null,
      items: [
        { page: "overview", label: "Tổng quan" },
        { page: "trips", label: "Chuyến đi của tôi" },
        { page: "alerts", label: "Lịch sử cảnh báo" },
        { page: "mydata", label: "Dữ liệu của tôi" },
      ],
    },
  ],
  manager: [
    {
      title: null,
      items: [
        { page: "overview", label: "Tổng quan" },
        { page: "fleet", label: "Đội xe" },
        { page: "reports", label: "Báo cáo chuyến" },
        { page: "events", label: "Nhật ký sự kiện" },
        { page: "timeline", label: "Timeline mệt mỏi" },
        { page: "thresholds", label: "Ngưỡng (chỉ xem)" },
      ],
    },
  ],
  engineer: [{ title: null, items: ENGINEER }],
  admin: [
    {
      title: "Quản trị",
      items: [
        { page: "accounts", label: "Tài khoản" },
        { page: "devices", label: "Thiết bị" },
        { page: "access", label: "Nhật ký truy cập" },
      ],
    },
    { title: "Vận hành", items: ENGINEER },
  ],
};

export const HOME: Record<Role, PageKey> = { driver: "overview", manager: "overview", engineer: "thresholds", admin: "accounts" };

export function pagesOf(role: Role): PageKey[] {
  return NAV[role].flatMap((s) => s.items.map((i) => i.page));
}

/** The page of `#/dashboard/<page>` if this role has it, else the role's home. */
export function pageFromHash(hash: string, role: Role): PageKey {
  const m = /^#\/dashboard\/([a-z]+)/.exec(hash);
  const page = m?.[1] as PageKey | undefined;
  return page && pagesOf(role).includes(page) ? page : HOME[role];
}

export const pageHref = (page: PageKey) => `#/dashboard/${page}`;

export function pageLabel(role: Role, page: PageKey): string {
  return NAV[role].flatMap((s) => s.items).find((i) => i.page === page)?.label ?? "";
}
