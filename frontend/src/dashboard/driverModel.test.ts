import { describe, expect, it } from "vitest";
import { demoTripSummary } from "../hud/demo";
import type { TripReport } from "../lib/types";
import { driverMonth, newestFirst, tripFromHash, tripHref } from "./driverModel";

const report = (trip: string, started: string, over: Partial<TripReport["summary"]> = {}): TripReport => ({
  trip_id: trip,
  device_id: "dev 07",
  driver_id: "drv-001",
  received_at: started,
  rating: "good",
  reviewed_by: null,
  reviewed_at: null,
  summary: { ...demoTripSummary(), trip_id: trip, started_at: started, ...over },
});

describe("M61 driver pages", () => {
  it("adds up the last 30 days", () => {
    const m = driverMonth([
      report("a", "2026-10-01T08:00:00Z", { driving_s: 3600, false_alarms: 1 }),
      report("b", "2026-10-02T08:00:00Z", { driving_s: 1800, alerts_by_level: { "1": 1, "2": 0, "3": 1 } }),
    ]);
    expect(m).toEqual({ trips: 2, drivingS: 5400, reminders: 3 + 2, falseAlarms: 1 });
    expect(driverMonth([])).toEqual({ trips: 0, drivingS: 0, reminders: 0, falseAlarms: 0 });
  });

  it("puts the newest trip first", () => {
    const list = newestFirst([report("old", "2026-09-30T08:00:00Z"), report("new", "2026-10-02T08:00:00Z")]);
    expect(list.map((r) => r.trip_id)).toEqual(["new", "old"]);
  });

  it("links a trip and reads the link back", () => {
    const href = tripHref("trips", { device_id: "dev 07", trip_id: "trip/1" });
    expect(href).toBe("#/dashboard/trips/dev%2007/trip%2F1");
    expect(tripFromHash(href)).toEqual({ deviceId: "dev 07", tripId: "trip/1" });
    expect(tripFromHash("#/dashboard/trips")).toBeNull();
  });
});
