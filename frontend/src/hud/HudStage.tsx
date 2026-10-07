// The HUD's 1280 x 800 stage (M58): the redesign is drawn for one landscape screen, so on any landscape
// screen at least 1024 px wide the whole layout is scaled to fit (letterboxed on the screen's own
// background), exactly as designed: bigger screens get bigger type, short ones never overflow.
// Phones and portrait tablets keep the fluid, stacked layout.
import { useEffect, useState, type CSSProperties, type ReactNode } from "react";

export const STAGE_W = 1280;
export const STAGE_H = 800;

/** Scale of the stage for a viewport, or null for the fluid layout. Pure, unit-tested. */
export function stageScale(width: number, height: number): number | null {
  if (width < 1024 || width / height < 1.2) return null;
  return Math.min(width / STAGE_W, height / STAGE_H);
}

function useStageScale(): number | null {
  const read = () => (typeof window === "undefined" ? null : stageScale(window.innerWidth, window.innerHeight));
  const [scale, setScale] = useState(read);
  useEffect(() => {
    const onResize = () => setScale(read());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return scale;
}

interface Props {
  /** Classes of the whole screen: background, text colour, L1 / L2 ring at the screen's edge. */
  className: string;
  style?: CSSProperties;
  /** Behind the stage, full screen (L3 pulse). */
  underlay?: ReactNode;
  /** Grid rows of the stage, e.g. ["72px", "minmax(0,1fr)", "auto"]. */
  rows: string[];
  /** Classes of the stage grid. */
  stageClassName?: string;
  children: ReactNode;
  /** Dialogs and toasts: outside the scaled stage, so `fixed` means the screen. */
  overlay?: ReactNode;
}

export default function HudStage({ className, style, underlay, rows, stageClassName = "", children, overlay }: Props) {
  const scale = useStageScale();
  const stage: CSSProperties = scale
    ? {
        position: "absolute",
        width: STAGE_W,
        height: STAGE_H,
        left: `calc((100vw - ${STAGE_W * scale}px) / 2)`,
        top: `calc((100dvh - ${STAGE_H * scale}px) / 2)`,
        transform: `scale(${scale})`,
        transformOrigin: "top left",
      }
    : {};
  return (
    <div
      style={style}
      className={`relative isolate min-h-dvh overflow-hidden font-hud antialiased [color-scheme:dark] ${scale ? "h-dvh" : ""} ${className}`}
    >
      {underlay}
      <div
        style={{ ...stage, gridTemplateRows: rows.join(" ") }}
        className={`isolate grid grid-cols-[minmax(0,1fr)] ${scale ? "" : "min-h-dvh"} ${stageClassName}`}
        data-stage={scale ? "fixed" : "fluid"}
      >
        <div aria-hidden className="dg-backdrop" />
        {children}
      </div>
      {overlay}
    </div>
  );
}
