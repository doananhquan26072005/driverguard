// Client for the in-car HUD server of the edge agent (edge_agent/hud/server.py, 127.0.0.1 only).
import type { HudSnapshot, TripDelivery, TripSummary, VehicleAction } from "../lib/types";

export const EDGE_URL: string = import.meta.env.VITE_EDGE_URL ?? "http://127.0.0.1:8765";
/** The driving simulator (tools/drive_sim.py): speed + turn signal for #/live. */
export const DRIVE_SIM_URL: string = import.meta.env.VITE_DRIVE_SIM_URL ?? "http://127.0.0.1:8766/can";

export async function fetchState(signal?: AbortSignal): Promise<HudSnapshot> {
  const resp = await fetch(`${EDGE_URL}/state`, { signal, cache: "no-store" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  return (await resp.json()) as HudSnapshot;
}

export type FeedbackResult = "recorded" | "duplicate" | "expired" | "unknown" | "offline";

export async function sendFalseAlarm(eventId: string): Promise<FeedbackResult> {
  try {
    const resp = await fetch(`${EDGE_URL}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_id: eventId }),
    });
    const body = (await resp.json()) as { status?: string };
    return (body.status as FeedbackResult) ?? (resp.ok ? "recorded" : "unknown");
  } catch {
    return "offline";
  }
}

export interface TripEnd {
  summary: TripSummary;
  delivery: TripDelivery;
}

/** "Kết thúc chuyến": the edge agent builds the trip summary, queues it for the backend, stops. */
export async function endEdgeTrip(): Promise<TripEnd> {
  const resp = await fetch(`${EDGE_URL}/end-trip`, { method: "POST" });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const body = (await resp.json()) as { summary: TripSummary };
  return { summary: body.summary, delivery: "device" };
}

/** "Đổi tài xế": the edge agent applies it on its next frame. */
export async function sendVehicle(action: VehicleAction): Promise<boolean> {
  try {
    const resp = await fetch(`${EDGE_URL}/vehicle`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action }),
    });
    return resp.ok;
  } catch {
    return false;
  }
}

/** Where the HUD gets its state: the edge agent's HUD server, or the in-browser agent (#/live). */
export interface HudSource {
  address: string; // shown when the link is down
  state(signal?: AbortSignal): Promise<HudSnapshot>;
  /** A source in the same page (#/live) hands over the snapshot the moment something urgent changes
   *  (M50): the alert sound does not wait for the next poll. Returns the unsubscribe. */
  subscribe?(listener: (snap: HudSnapshot) => void): () => void;
  falseAlarm(eventId: string): Promise<FeedbackResult>;
  endTrip?(): Promise<TripEnd>;
  vehicle?(action: VehicleAction): Promise<boolean>;
  /** The camera of this page (#/live only), shown in the enrollment frame. Never stored or sent; the
   *  device HUD has none: the edge agent never hands an image to the screen. */
  cameraStream?(): MediaStream | null;
}

export const edgeSource: HudSource = {
  address: EDGE_URL,
  state: fetchState,
  falseAlarm: sendFalseAlarm,
  endTrip: endEdgeTrip,
  vehicle: sendVehicle,
};
