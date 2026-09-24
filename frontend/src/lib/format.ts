// Formatting and small pure helpers (unit-tested in format.test.ts).

const timeFmt = new Intl.DateTimeFormat("vi-VN", { hour: "2-digit", minute: "2-digit", second: "2-digit" });
const dateTimeFmt = new Intl.DateTimeFormat("vi-VN", {
  day: "2-digit",
  month: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

export function formatTime(iso: string | number | Date): string {
  return timeFmt.format(new Date(iso));
}

export function formatDateTime(iso: string | number | Date): string {
  return dateTimeFmt.format(new Date(iso));
}

export function formatPercent(ratio: number | null | undefined, digits = 0): string {
  if (ratio == null || Number.isNaN(ratio)) return "–";
  return `${formatNumber(ratio * 100, digits)}%`;
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value == null || Number.isNaN(value)) return "–";
  return value.toLocaleString("vi-VN", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

/** "12 giây trước", "3 phút trước" */
export function ago(seconds: number): string {
  if (seconds < 60) return `${Math.max(0, Math.round(seconds))} giây trước`;
  if (seconds < 3600) return `${Math.round(seconds / 60)} phút trước`;
  return `${Math.round(seconds / 3600)} giờ trước`;
}

/** Local time of day from the CAN clock (hours, 0..24) -> "02:30". */
export function clockText(hour: number | undefined): string {
  if (hour == null) return "--:--";
  const h = Math.floor(hour) % 24;
  const m = Math.floor((hour - Math.floor(hour)) * 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}

export type RangeKey = "24h" | "7d" | "30d" | "all";

export const RANGES: { key: RangeKey; label: string }[] = [
  { key: "24h", label: "24 giờ" },
  { key: "7d", label: "7 ngày" },
  { key: "30d", label: "30 ngày" },
  { key: "all", label: "Tất cả" },
];

/** Start of a time range as an ISO string, or undefined for "all". */
export function rangeStart(range: RangeKey, now: number = Date.now()): string | undefined {
  const hours = { "24h": 24, "7d": 24 * 7, "30d": 24 * 30, all: 0 }[range];
  return hours ? new Date(now - hours * 3600_000).toISOString() : undefined;
}

/** Query string from an object, skipping empty values. */
export function query(params: Record<string, string | number | boolean | undefined | null>): string {
  const q = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === "" || v === false) continue;
    q.set(k, String(v));
  }
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** Keys whose value differs from the stored version (what a PUT needs to send). */
export function changedValues(
  edited: Record<string, string>,
  stored: Record<string, number>,
): { values: Record<string, number>; invalid: string[] } {
  const values: Record<string, number> = {};
  const invalid: string[] = [];
  for (const [key, raw] of Object.entries(edited)) {
    if (raw.trim() === "") continue;
    const n = Number(raw.replace(",", "."));
    if (!Number.isFinite(n)) {
      invalid.push(key);
      continue;
    }
    if (stored[key] !== n) values[key] = n;
  }
  return { values, invalid };
}
