// Shapes returned by the backend (backend/schemas.py) and the in-car HUD server
// (edge_agent/hud/server.py). Metadata only: there is never an image field.

export type Role = "admin" | "engineer" | "manager" | "driver";
export type Level = 0 | 1 | 2 | 3;
export type Reason = "microsleep" | "drowsy_score" | "off_road" | "phone" | "no_face" | "trend" | "blink_rate";

export interface Session {
  token: string;
  username: string;
  role: Role;
  driverId: string | null;
  expiresAt: number; // ms epoch
}

export interface EventRecord {
  event_id: string;
  device_id: string;
  driver_id: string | null;
  trip_id: string;
  ts: string;
  type: "drowsiness" | "distraction";
  level: Level;
  reasons: Reason[];
  drowsy_score: number;
  distraction_score: number;
  speed_kmh: number | null;
  metrics: Record<string, number | null>;
  received_at: string;
  feedback: "false_alarm" | null;
  feedback_at: string | null;
}

export interface SampleRecord {
  ts: string;
  trip_id: string;
  device_id: string;
  driver_id: string | null;
  drowsy_score: number;
  perclos_60s: number | null;
  max_level: Level;
}

export interface Timeline {
  samples: SampleRecord[];
  events: EventRecord[];
}

export interface Trip {
  trip_id: string;
  device_id: string;
  driver_id: string | null;
  start: string;
  end: string;
  events: number;
  max_level: Level;
}

export interface Stats {
  total: number;
  false_alarms: number;
  by_level: Record<string, number>;
  by_reason: Record<string, { total: number; false_alarms: number }>;
}

export interface ThresholdSpec {
  min: number;
  max: number;
  unit: string;
}

export interface Thresholds {
  version: number;
  values: Record<string, number>;
  updated_by: string | null;
  updated_at: string | null;
  specs: Record<string, ThresholdSpec>;
}

export interface HudAlert {
  event_id: string;
  level: Level;
  reasons: Reason[];
  at: number; // seconds epoch
  feedback: "false_alarm" | null;
}

export interface HudSnapshot {
  connected: boolean;
  updated_at?: number; // seconds epoch
  level: Level;
  reasons: Reason[];
  drowsy_score?: number;
  distraction_score?: number;
  speed_kmh?: number | null;
  clock_hour?: number;
  night?: boolean;
  eyes_closed_s?: number;
  perclos_60s?: number;
  fps?: number;
  alerts: HudAlert[];
}
