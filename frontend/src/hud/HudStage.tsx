// The HUD's stage: the design is drawn for one screen, so the whole layout is scaled to fit it
// (letterboxed on the screen's own background), exactly as designed: bigger screens get bigger type,
// short ones never overflow.
// - landscape, at least 1024 px wide: the 1280 x 800 stage (M58), two columns
// - portrait, at least 640 px wide (the car's 10 inch upright screen): the 800 x 1280 stage (M89),
//   the same cards stacked, nothing below the fold
// - phones and near-square windows: the fluid, stacked layout, which scrolls
// Breakpoints inside a stage follow the stage's width, not the screen's (container "hud": the
// hud-sm / hud-md / hud-lg variants of index.css), so a stage looks the same at any scale.
// Inside a <StageFrame.Provider> (the guide, M102) the "screen" is that box, not the window.
import { createContext, useContext, useEffect, useState, type CSSProperties, type ReactNode } from "react";

export const STAGE_W = 1280;
export const STAGE_H = 800;
const WIDE_MIN_W = 1024;
const TALL_MIN_W = 640; // hud-sm: the stage's padding and tile sizes are the tablet's
const MIN_RATIO = 1.2; // long side / short side; squarer than this is neither

export interface StageLayout {
  shape: "landscape" | "portrait";
  width: number; // of the design, before scaling
  height: number;
  scale: number;
}

/** The fixed stage for a viewport, or null for the fluid layout. Pure, unit-tested. */
export function stageLayout(width: number, height: number): StageLayout | null {
  const fit = (shape: StageLayout["shape"], w: number, h: number) => ({
    shape,
    width: w,
    height: h,
    scale: Math.min(width / w, height / h),
  });
  if (width >= WIDE_MIN_W && width / height >= MIN_RATIO) return fit("landscape", STAGE_W, STAGE_H);
  if (width >= TALL_MIN_W && height / width >= MIN_RATIO) return fit("portrait", STAGE_H, STAGE_W);
  return null;
}

/** A box that stands in for the screen: the stage fits it, and nothing is sized from the window. */
export const StageFrame = createContext<{ width: number; height: number } | null>(null);

function useStageLayout(): StageLayout | null {
  const read = () => (typeof window === "undefined" ? null : stageLayout(window.innerWidth, window.innerHeight));
  const [layout, setLayout] = useState(read);
  useEffect(() => {
    const onResize = () => setLayout(read());
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);
  return layout;
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
  const frame = useContext(StageFrame);
  const windowLayout = useStageLayout();
  const layout = frame ? stageLayout(frame.width, frame.height) : windowLayout;
  const stage: CSSProperties = layout
    ? {
        position: "absolute",
        width: layout.width,
        height: layout.height,
        left: frame ? (frame.width - layout.width * layout.scale) / 2 : `calc((100vw - ${layout.width * layout.scale}px) / 2)`,
        top: frame ? (frame.height - layout.height * layout.scale) / 2 : `calc((100dvh - ${layout.height * layout.scale}px) / 2)`,
        transform: `scale(${layout.scale})`,
        transformOrigin: "top left",
      }
    : {};
  return (
    <div
      style={frame ? { ...style, width: frame.width, height: frame.height } : style}
      className={`relative isolate overflow-hidden font-hud antialiased [color-scheme:dark] ${frame ? "" : layout ? "min-h-dvh h-dvh" : "min-h-dvh"} ${className}`}
    >
      {underlay}
      <div
        style={{ ...stage, gridTemplateRows: rows.join(" ") }}
        className={`@container/hud isolate grid grid-cols-[minmax(0,1fr)] ${layout ? "" : frame ? "min-h-full" : "min-h-dvh"} ${stageClassName}`}
        data-stage={layout ? "fixed" : "fluid"}
        data-shape={layout?.shape}
      >
        <div aria-hidden className="dg-backdrop" />
        {children}
      </div>
      {overlay}
    </div>
  );
}
