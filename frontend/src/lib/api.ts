// Backend client (FastAPI, backend/app.py). The JWT lives in sessionStorage only:
// it is gone when the tab closes.
import { dayRange, query, type RangeKey, rangeStart } from "./format";
import type {
  AccessLogRow,
  DeletionRequest,
  EventRecord,
  FleetDevice,
  RefusalReason,
  Role,
  Session,
  Stats,
  ThresholdVersion,
  Thresholds,
  Timeline,
  Trip,
  TripReport,
} from "./types";

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

// End-of-trip reports: drivers get their own, the higher roles every driver's.
export function getTripReports(s: Session, range: RangeKey, unreviewedOnly = false): Promise<TripReport[]> {
  return request(
    `/api/v1/trip-reports${query({ since: rangeStart(range), unreviewed_only: unreviewedOnly || undefined, limit: 200 })}`,
    {},
    s,
  );
}

export function reviewTripReport(s: Session, r: Pick<TripReport, "device_id" | "trip_id">): Promise<TripReport> {
  const path = `/api/v1/trip-reports/${encodeURIComponent(r.device_id)}/${encodeURIComponent(r.trip_id)}/review`;
  return request(path, { method: "POST" }, s);
}

// Fleet overview (M33): every vehicle, online or quiet, with its alerts of one local day.
export function getFleet(s: Session, day: string): Promise<FleetDevice[]> {
  return request(`/api/v1/fleet${query({ ...dayRange(day) })}`, {}, s);
}

// Data policy numbers (public): how long the server keeps metadata.
export function getPolicy(): Promise<{
  retention_events_days: number;
  retention_summaries_days: number;
  retention_access_log_days?: number;
}> {
  return request("/api/v1/policy");
}

// Access log (M41): admins get all of it, a driver gets who looked at their own data.
export function getAccessLog(s: Session, range: RangeKey): Promise<AccessLogRow[]> {
  const path = s.role === "driver" ? "/api/v1/access-log/mine" : "/api/v1/access-log";
  return request(`${path}${query({ since: rangeStart(range), limit: 500 })}`, {}, s);
}

// A driver's own data (M48): everything stored about them as JSON, and a request to delete it.
export function getMyData(s: Session): Promise<Record<string, unknown>> {
  return request("/api/v1/me/data", {}, s);
}

export function getMyDeletionRequest(s: Session): Promise<DeletionRequest | null> {
  return request("/api/v1/me/deletion-request", {}, s);
}

export function requestMyDeletion(s: Session): Promise<DeletionRequest> {
  return request("/api/v1/me/deletion-request", { method: "POST" }, s);
}

export function getDeletionRequests(s: Session): Promise<DeletionRequest[]> {
  return request("/api/v1/deletion-requests", {}, s);
}

export function decideDeletion(s: Session, id: number, reason?: RefusalReason): Promise<DeletionRequest> {
  const body = reason ? { action: "refuse", reason } : { action: "delete" };
  return request(`/api/v1/deletion-requests/${id}`, { method: "POST", body: JSON.stringify(body) }, s);
}

export function getThresholds(s: Session): Promise<Thresholds> {
  return request("/api/v1/thresholds", {}, s);
}

/** trialDevices: only these devices get the new version (M47); empty = the whole fleet at once. */
export function putThresholds(s: Session, values: Record<string, number>, trialDevices: string[] = []): Promise<Thresholds> {
  const body = trialDevices.length ? { values, trial_devices: trialDevices } : { values };
  return request("/api/v1/thresholds", { method: "PUT", body: JSON.stringify(body) }, s);
}

export function getThresholdVersions(s: Session): Promise<ThresholdVersion[]> {
  return request("/api/v1/thresholds/versions", {}, s);
}

/** Give a stored version to the whole fleet: a trial that went well, or an older one (roll back). */
export function rolloutThresholds(s: Session, version: number): Promise<Thresholds> {
  return request("/api/v1/thresholds/rollout", { method: "POST", body: JSON.stringify({ version }) }, s);
}

// In-browser agent (#/live): tuned thresholds and event batches with the user's token.
export function getWebThresholds(s: Session): Promise<Thresholds> {
  return request("/api/v1/web/thresholds", {}, s);
}

export function postWebBatch(s: Session, body: string): Promise<{ accepted: number }> {
  return request("/api/v1/web/events", { method: "POST", body }, s);
}

/** Same as backend.app.web_device_id: the user's browser as a device. */
export function webDeviceId(username: string): string {
  return `web-${username}`.slice(0, 48);
}

// Accounts and devices (admin, M63). The device key comes back once, at creation, and is never stored here.
export interface UserRow {
  username: string;
  role: Role;
  driver_id: string | null;
}
export function getUsers(s: Session): Promise<UserRow[]> {
  return request("/api/v1/users", {}, s);
}
export function createUser(s: Session, u: UserRow & { password: string }): Promise<UserRow> {
  return request("/api/v1/users", { method: "POST", body: JSON.stringify(u) }, s);
}
export function createDevice(s: Session, d: { device_id: string; driver_id: string | null }): Promise<{ device_id: string; driver_id: string | null; device_key: string | null }> {
  return request("/api/v1/devices", { method: "POST", body: JSON.stringify(d) }, s);
}
