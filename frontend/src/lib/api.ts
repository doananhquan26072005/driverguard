// Backend client (FastAPI, backend/app.py). The JWT lives in sessionStorage only:
// it is gone when the tab closes.
import { query, type RangeKey, rangeStart } from "./format";
import type { EventRecord, Role, Session, Stats, Thresholds, Timeline, Trip } from "./types";

export const API_URL: string = import.meta.env.VITE_API_URL ?? "http://localhost:8100";
const SESSION_KEY = "driverguard.session";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function detailText(detail: unknown): string {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((d) => (typeof d === "object" && d && "msg" in d ? String(d.msg) : String(d))).join("; ");
  }
  return "Lỗi không xác định";
}

export function loadSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    if (!raw) return null;
    const s = JSON.parse(raw) as Session;
    return s.expiresAt > Date.now() ? s : null;
  } catch {
    return null;
  }
}

export function saveSession(s: Session | null): void {
  try {
    if (s) sessionStorage.setItem(SESSION_KEY, JSON.stringify(s));
    else sessionStorage.removeItem(SESSION_KEY);
  } catch {
    // storage unavailable (private mode): the session just won't survive a reload
  }
}

async function request<T>(path: string, init: RequestInit = {}, session?: Session | null): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (session) headers.Authorization = `Bearer ${session.token}`;
  let resp: Response;
  try {
    resp = await fetch(`${API_URL}${path}`, { ...init, headers: { ...headers, ...(init.headers ?? {}) } });
  } catch {
    throw new ApiError(0, `Không kết nối được máy chủ ${API_URL}`);
  }
  if (!resp.ok) {
    let message = `HTTP ${resp.status}`;
    try {
      message = detailText((await resp.json()).detail);
    } catch {
      // body was not JSON
    }
    throw new ApiError(resp.status, message);
  }
  return (await resp.json()) as T;
}

export async function login(username: string, password: string): Promise<Session> {
  const t = await request<{ access_token: string; role: Role; expires_in: number }>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  const partial = { token: t.access_token, username, role: t.role, driverId: null, expiresAt: 0 } as Session;
  const me = await request<{ driver_id: string | null }>("/auth/me", {}, partial);
  return { ...partial, driverId: me.driver_id, expiresAt: Date.now() + t.expires_in * 1000 };
}

export interface EventFilters {
  range: RangeKey;
  minLevel: number;
  driverId: string;
  falseAlarmOnly: boolean;
}

export function getEvents(s: Session, f: EventFilters, limit = 200): Promise<EventRecord[]> {
  const q = query({
    since: rangeStart(f.range),
    min_level: f.minLevel || undefined,
    driver_id: f.driverId || undefined,
    false_alarm_only: f.falseAlarmOnly,
    limit,
  });
  return request(`/api/v1/events${q}`, {}, s);
}

export function getStats(s: Session, range: RangeKey, driverId = ""): Promise<Stats> {
  return request(`/api/v1/stats${query({ since: rangeStart(range), driver_id: driverId || undefined })}`, {}, s);
}

export function getTrips(s: Session, range: RangeKey): Promise<Trip[]> {
  return request(`/api/v1/trips${query({ since: rangeStart(range), limit: 200 })}`, {}, s);
}

export function getTimeline(s: Session, tripId: string): Promise<Timeline> {
  return request(`/api/v1/timeline${query({ trip_id: tripId })}`, {}, s);
}

export function getThresholds(s: Session): Promise<Thresholds> {
  return request("/api/v1/thresholds", {}, s);
}

export function putThresholds(s: Session, values: Record<string, number>): Promise<Thresholds> {
  return request("/api/v1/thresholds", { method: "PUT", body: JSON.stringify({ values }) }, s);
}
