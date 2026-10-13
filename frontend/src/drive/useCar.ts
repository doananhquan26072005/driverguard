// The simulated car of the driving controls, shared by #/drive and the panel beside the HUD on #/live
// (M103): its physics (sim.ts) at tick_hz, stepped by the time that really passed, and the commands of
// the buttons / keys.
import { useCallback, useEffect, useRef, useState } from "react";
import { steadyInterval } from "../lib/ticker";
import { type CarState, command, DRIVE_KEYS, DRIVE_SIM, type DriveCommand, PARKED, step } from "./sim";

export interface Car {
  car: CarState; // for rendering
  carRef: React.RefObject<CarState>; // the car itself: ticks and sends read it even while the tab is hidden
  act: (cmd: DriveCommand) => void;
  touched: boolean; // a button or key was used at least once
}

/** keys: also W / S / Space / C / A / D / X and the arrows (tools/drive_sim.py's), outside text fields. */
export function useCar({ keys = false }: { keys?: boolean } = {}): Car {
  const [car, setCar] = useState(PARKED);
  const [touched, setTouched] = useState(false);
  const carRef = useRef(PARKED);
  const update = useCallback((f: (c: CarState) => CarState) => {
    carRef.current = f(carRef.current);
    setCar(carRef.current);
  }, []);

  // A late tick does not slow the car.
  useEffect(() => {
    let last = performance.now();
    return steadyInterval(() => {
      const now = performance.now();
      update((c) => step(c, (now - last) / 1000));
      last = now;
    }, 1000 / DRIVE_SIM.tickHz);
  }, [update]);

  const act = useCallback(
    (cmd: DriveCommand) => {
      setTouched(true);
      update((c) => command(c, cmd));
    },
    [update],
  );

  useEffect(() => {
    if (!keys) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      const cmd = DRIVE_KEYS[e.key];
      if (!cmd) return;
      e.preventDefault();
      act(cmd);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [keys, act]);

  return { car, carRef, act, touched };
}
