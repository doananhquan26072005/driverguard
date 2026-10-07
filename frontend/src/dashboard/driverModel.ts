// The driver's pages (M61): numbers of the last 30 days and the trip a link points to. Pure, unit-tested.
import type { TripReport } from "../lib/types";

export interface DriverMonth {
  trips: number;
  drivingS: number;
  reminders: number; // alerts of every level the driver was given
  falseAlarms: number; // alerts the driver flagged as false
}

export function driverMonth(reports: readonly TripReport[]): DriverMonth {
  return reports.reduce<DriverMonth>(
    (m, r) => ({
      trips: m.trips + 1,
      drivingS: m.drivingS + r.summary.driving_s,
      reminders: m.reminders + Object.values(r.summary.alerts_by_level).reduce((a, b) => a + (b ?? 0), 0),
      falseAlarms: m.falseAlarms + r.summary.false_alarms,
    }),
    { trips: 0, drivingS: 0, reminders: 0, falseAlarms: 0 },
  );
}

/** Newest trip first (by when it started). */
export function newestFirst(reports: readonly TripReport[]): TripReport[] {
  return [...reports].sort((a, b) => Date.parse(b.summary.started_at) - Date.parse(a.summary.started_at));
}

/** `#/dashboard/<page>/<device_id>/<trip_id>`: which trip a detail link opens, or null for the list. */
export function tripFromHash(hash: string): { deviceId: string; tripId: string } | null {
  const m = /^#\/dashboard\/[a-z]+\/([^/]+)\/([^/?#]+)/.exec(hash);
  return m ? { deviceId: decodeURIComponent(m[1]), tripId: decodeURIComponent(m[2]) } : null;
}

export const tripHref = (page: string, r: Pick<TripReport, "device_id" | "trip_id">) =>
  `#/dashboard/${page}/${encodeURIComponent(r.device_id)}/${encodeURIComponent(r.trip_id)}`;
