// The self-view of #/live (the small camera picture over the HUD): where it sits and how big it is
// (M100). It used to sit fixed at the bottom left, 176 px wide, over the "Cảnh báo này sai?" button
// (62 % of it in landscape) and over "Đổi tài xế" in portrait (roadmap M89). The driver can now drag it
// anywhere and make it smaller or larger; the choice is kept in this browser. Numbers only, no picture.

/** Widths in px, smallest first. The middle one is the size it always had. */
export const SELF_VIEW_WIDTHS: readonly number[] = [112, 176, 264];
const DEFAULT_SIZE = SELF_VIEW_WIDTHS.indexOf(176);
const MARGIN = 8; // px kept between the frame and the edge of the window
const STORE_KEY = "dg.live.selfview";

/** x / y: the frame's top-left corner in px of the window; null = where it always was (bottom left). */
export interface SelfViewPlace {
  x: number | null;
  y: number | null;
  size: number; // index into SELF_VIEW_WIDTHS
}

export const DEFAULT_PLACE: SelfViewPlace = { x: null, y: null, size: DEFAULT_SIZE };

/** The corner kept inside the window, whatever was asked for (a drag past the edge, a smaller window). */
export function clampCorner(x: number, y: number, frame: { width: number; height: number }, win: { width: number; height: number }): { x: number; y: number } {
  const fit = (v: number, size: number, room: number) => Math.round(Math.min(Math.max(v, MARGIN), Math.max(room - size - MARGIN, MARGIN)));
  return { x: fit(x, frame.width, win.width), y: fit(y, frame.height, win.height) };
}

/** One size up (+1) or down (-1); the same size at either end. */
export function resized(size: number, step: 1 | -1): number {
  return Math.min(Math.max(size + step, 0), SELF_VIEW_WIDTHS.length - 1);
}

/** A stored value as a place; anything else (nothing stored, another version, junk) is the default. */
export function parsePlace(raw: string | null): SelfViewPlace {
  try {
    const p = JSON.parse(raw ?? "null") as Partial<SelfViewPlace> | null;
    if (!p || typeof p !== "object") return DEFAULT_PLACE;
    const size = Number.isInteger(p.size) && p.size! >= 0 && p.size! < SELF_VIEW_WIDTHS.length ? p.size! : DEFAULT_SIZE;
    const placed = typeof p.x === "number" && typeof p.y === "number" && Number.isFinite(p.x) && Number.isFinite(p.y);
    return { x: placed ? p.x! : null, y: placed ? p.y! : null, size };
  } catch {
    return DEFAULT_PLACE;
  }
}

export function readPlace(): SelfViewPlace {
  try {
    return parsePlace(localStorage.getItem(STORE_KEY));
  } catch {
    return DEFAULT_PLACE; // storage blocked: the default place, every time
  }
}

export function writePlace(place: SelfViewPlace): void {
  try {
    localStorage.setItem(STORE_KEY, JSON.stringify(place));
  } catch {
    // storage unavailable (private mode): the place just won't be remembered
  }
}
