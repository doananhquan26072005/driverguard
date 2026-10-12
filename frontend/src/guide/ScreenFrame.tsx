// One screen of the product, drawn small inside the guide (M102): the real HudView / TripSummaryView on a
// scenario of #/hud-preview, in a box that stands in for the screen (hud/HudStage.tsx StageFrame) and is
// then scaled to fit the room the guide gives it (width and height: the guide never scrolls). A picture only: `inert`, so nothing in it takes a touch, the
// keyboard or a screen reader (the guide's own text says what the screen shows). No sound, no agent,
// no camera: fixed numbers.
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { demoTripSummary } from "../hud/demo";
import { SCENARIOS, snapshotFor } from "../hud/HudPreview";
import { STAGE_H, STAGE_W, StageFrame, stageLayout } from "../hud/HudStage";
import HudView from "../hud/HudView";
import TripSummaryView from "../hud/TripSummaryView";

const TICK_MS = 500; // the L3 screen counts the seconds the eyes stay closed
const nothing = () => undefined;

/** The shape this device's own HUD has: upright on an upright screen (the car's), else landscape. */
function deviceShape(): { width: number; height: number } {
  const upright = typeof window !== "undefined" && stageLayout(window.innerWidth, window.innerHeight)?.shape === "portrait";
  return upright ? { width: STAGE_H, height: STAGE_W } : { width: STAGE_W, height: STAGE_H };
}

export default function ScreenFrame({ scenario, label }: { scenario: string; label: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [frame, setFrame] = useState(deviceShape);
  const [scale, setScale] = useState(0); // 0: not measured yet, nothing drawn
  const [since, setSince] = useState(() => Date.now() / 1000);
  const [now, setNow] = useState(since);
  const [shown, setShown] = useState(scenario);
  if (shown !== scenario) {
    // A new screen starts its own clock (alert age, seconds with eyes closed).
    setShown(scenario);
    setSince(Date.now() / 1000);
    setNow(Date.now() / 1000);
  }

  useEffect(() => {
    const id = setInterval(() => setNow(Date.now() / 1000), TICK_MS);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    const fit = () => {
      const shape = deviceShape();
      const room = box.current;
      setFrame((f) => (f.width === shape.width ? f : shape));
      setScale(room ? Math.min(room.clientWidth / shape.width, room.clientHeight / shape.height) : 0);
    };
    fit();
    window.addEventListener("resize", fit);
    const seen = typeof ResizeObserver === "undefined" ? null : new ResizeObserver(fit);
    if (seen && box.current) seen.observe(box.current);
    return () => {
      window.removeEventListener("resize", fit);
      seen?.disconnect();
    };
  }, []);

  const s = SCENARIOS.find((x) => x.key === scenario) ?? SCENARIOS[0];
  const snap = snapshotFor(s, false, now, since);
  // transform: the scaled copy, and the containing block of anything `fixed` inside the HUD. The two
  // type sizes that follow the window's width (index.css) are pinned to what a 1280 px screen gives.
  const screen: CSSProperties = {
    width: frame.width,
    height: frame.height,
    transform: `scale(${scale})`,
    transformOrigin: "top left",
    ["--text-hud-title" as string]: "30px",
    ["--text-hud-display" as string]: "76.8px",
  };

  return (
    <div ref={box} className="guide-screen-room">
      <div
        className="guide-screen"
        role="img"
        aria-label={`Hình minh hoạ màn hình: ${label}`}
        style={{ width: frame.width * scale, height: frame.height * scale }}
        data-scenario={s.key}
      >
        {scale > 0 && (
          <div style={screen} inert>
            <StageFrame.Provider value={frame}>
              {s.key === "trip" ? (
                <TripSummaryView summary={demoTripSummary()} delivery="sent" onDone={nothing} />
              ) : (
                <HudView
                  snap={snap}
                  link={s.link ?? "ok"}
                  stale={false}
                  cameraLost={s.cameraLost ?? false}
                  demo={false}
                  now={now}
                  sound={!s.soundBlocked}
                  feedbackTarget={snap.alerts[0] ?? null}
                  toast={null}
                  edgeUrl=""
                  onEnableSound={nothing}
                  onFalseAlarm={nothing}
                  onEndTrip={nothing}
                  onVehicle={nothing}
                />
              )}
            </StageFrame.Provider>
          </div>
        )}
      </div>
    </div>
  );
}
