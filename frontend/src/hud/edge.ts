// Client for the in-car HUD server of the edge agent (edge_agent/hud/server.py, 127.0.0.1 only).
import type { HudSnapshot } from "../lib/types";

export const EDGE_URL: string = import.meta.env.VITE_EDGE_URL ?? "http://127.0.0.1:8765";

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

/** Where the HUD gets its state: the edge agent's HUD server, or the in-browser agent (#/live). */
export interface HudSource {
  address: string; // shown when the link is down
  state(signal?: AbortSignal): Promise<HudSnapshot>;
  falseAlarm(eventId: string): Promise<FeedbackResult>;
}

export const edgeSource: HudSource = { address: EDGE_URL, state: fetchState, falseAlarm: sendFalseAlarm };
