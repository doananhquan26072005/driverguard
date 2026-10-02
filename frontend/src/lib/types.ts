// Shapes returned by the backend (backend/schemas.py) and the in-car HUD server
// (edge_agent/hud/server.py). Metadata only: there is never an image field.

export type Role = "admin" | "engineer" | "manager" | "driver";
export type Level = 0 | 1 | 2 | 3;
export type Reason =
  | "microsleep"
  | "drowsy_score"
  | "off_road"
  | "phone"
  | "no_face" // v1 only: a lost face is now "monitoring unavailable", not an alert
  | "trend"
  | "blink_rate"
  | "camera_lost" // system events: the device stopped / resumed monitoring
  | "camera_restored"
  | "driver_enrolled" // system event: from now on judged with the driver's own baselines
  | "monitoring_unavailable" // system events: face lost while moving (PRD FR-6) / back
  | "monitoring_restored"
  | "driver_changed" // system event: "Đổi tài xế" on the HUD, a new driver enrolls
  | "vehicle_signal_lost" // system events: vehicle link lost while driving (speed unknown) / back
  | "vehicle_signal_restored"
  | "agent_error" // system events (M28): frames keep failing, not monitored / processing again
  | "agent_recovered"
  | "low_fps" // system events (M28): too slow for a while, alerts may be late / back up
  | "fps_restored";

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
  type: "drowsiness" | "distraction" | "system";
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

// Driver enrollment (edge_agent/perception/enrollment.py): at a stop, the driver agrees on the consent
// screen ("consent"; "Để sau" = "later" until the next stop), then three steps, once per trip.
export type EnrollStep = "look_camera" | "look_road" | "close_eyes";
export type EnrollStatus = "off" | "waiting" | "consent" | "later" | EnrollStep | "done" | "failed";
export type EnrollHint =
  | "stop_vehicle"
  | "face_not_found"
  | "too_dark"
  | "look_camera"
  | "look_road"
  | "hold_still"
  | "open_eyes"
  | "close_mouth"
  | "close_eyes";

export interface HudEnrollment {
  status: EnrollStatus;
  progress: number; // 0..1 of the current step
  hint: EnrollHint | null;
  attempts: number; // steps redone so far
  duration_s?: number | null; // first step -> done, once enrolled
}

// End-of-trip summary (edge_agent/decision/trip_summary.py, block 11). Numbers only.
export type TripRating = "good" | "attention" | "risk";
export type RatingReason = "microsleep" | "frequent_alerts" | "tired_minutes" | "low_coverage";
export type SuggestionCode =
  | "rest_now"
  | "rest_after"
  | "regular_breaks"
  | "phone_away"
  | "eyes_on_road"
  | "check_camera"
  | "enroll";

export interface TripMinute {
  minute: number;
  drowsy_score: number;
  max_level: Level;
  moving: boolean;
}

export interface TripSummary {
  trip_id: string;
  started_at: string;
  ended_at: string;
  duration_s: number;
  driving_s: number;
  stopped_s: number;
  rests: number;
  longest_drive_s: number;
  avg_speed_kmh: number | null;
  speed_source: "simulated" | "can";
  alerts_by_level: Record<"1" | "2" | "3", number>;
  alerts_by_reason: Partial<Record<Reason, number>>;
  false_alarms: number;
  microsleeps: number;
  longest_closure_s: number;
  yawns: number;
  nods: number;
  brow_raises: number;
  off_road_s: number;
  phone_s: number;
  monitored_frac: number | null;
  unavailable_s: number;
  camera_lost_s: number;
  vehicle_signal_lost_s?: number; // M26: vehicle link lost while driving (older agents omit it)
  enrolled: boolean;
  driver_changes: number;
  drowsy_mean: number;
  drowsy_p90: number;
  drowsy_max: number;
  first_tired_min: number | null;
  score_l1: number;
  score_l2: number;
  rating: TripRating;
  rating_reasons: RatingReason[];
  suggestions: { code: SuggestionCode; minutes?: number | null }[];
  minutes: TripMinute[];
}

/** A stored trip summary (backend /api/v1/trip-reports): who sent it, whether a higher role read it. */
export interface TripReport {
  trip_id: string;
  device_id: string;
  driver_id: string | null;
  received_at: string;
  rating: TripRating;
  reviewed_by: string | null;
  reviewed_at: string | null;
  summary: TripSummary;
}

/** Where the summary went when the driver ended the trip:
 *  sent (backend accepted it), failed (browser: not sent, and nothing retries after the camera stops),
 *  local (guest: nothing leaves the browser), device (the edge agent's offline queue sends it). */
export type TripDelivery = "sent" | "failed" | "local" | "device";

/** Vehicle state for the HUD. Parked / driving follows the speed (0 km/h = parked), no button.
 *  source "sim" = the driving simulator (tools/drive_sim.py); connected false = it is not running,
 *  so the vehicle stands still at 0 km/h. Other sources: a scripted CAN scenario (device --scenario).
 *  signal_lost (M26): a signal had come in and the link went quiet; the driver is told. While driving
 *  the speed is unknown (null) and it is still monitored as driving; while parked it stays parked. */
export interface HudVehicle {
  source: string | null;
  connected: boolean;
  speed_kmh: number | null;
  turn_signal: "left" | "right" | null;
  driving: boolean;
  signal_lost?: boolean;
}

// "Đổi tài xế", and the driver's answer on the enrollment consent screen ("Đồng ý" / "Để sau").
export type VehicleAction = "change_driver" | "enroll_start" | "enroll_later";

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
  camera_lost?: boolean; // camera unplugged: driver not monitored, device reconnecting
  processing_error?: boolean; // M28: frames keep failing: driver not monitored, the loop retries
  low_fps?: boolean; // M28: too slow for a while: alerts may be late
  unavailable?: boolean; // face lost while moving (PRD FR-6): not monitored, no alerts
  trip_ended?: boolean; // the trip summary was built (device HUD server)
  vehicle?: HudVehicle;
  feedback_window_s?: number; // "false alarm" button hidden this long after an alert
  enrollment?: HudEnrollment;
  alerts: HudAlert[];
}
