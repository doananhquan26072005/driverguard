// PRD FR-17: every state set by hand on the preview screen is logged with the tags `simulated` and
// `forced`. The log lives in this page only (and in the file the operator downloads after a
// comprehension session): it is never sent to the backend, so a forced state cannot reach any number.
// Pure, unit-tested in forcedLog.test.ts.
import type { EventTag } from "../lib/types";

export const FORCED_TAGS: EventTag[] = ["simulated", "forced"];
export const FORCED_LOG_MAX = 500; // oldest entries dropped beyond this

export interface ForcedEntry {
  at: string; // ISO time the state was picked
  state: string; // scenario key, e.g. "l3"
  label: string; // what the button says
  from: string | null; // the state before it
  night: boolean;
  tags: EventTag[];
}

export function forcedEntry(state: string, label: string, from: string | null, night: boolean, now = new Date()): ForcedEntry {
  return { at: now.toISOString(), state, label, from, night, tags: [...FORCED_TAGS] };
}

export function appendForced(log: ForcedEntry[], entry: ForcedEntry): ForcedEntry[] {
  return [...log, entry].slice(-FORCED_LOG_MAX);
}

/** The file the operator keeps: what was shown when, and that none of it is a measurement. */
export function forcedLogFile(log: ForcedEntry[]): string {
  return JSON.stringify(
    { note: "States forced by hand on the HUD preview (PRD FR-17). Not measurements: never used for any metric.", entries: log },
    null,
    1,
  );
}
