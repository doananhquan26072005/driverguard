// The simulated car of the web driving controls (#/drive, M31): the same model as
// tools/drive_sim.py. Commands change the target speed, step(dt) moves the speed toward it at a
// car's pace. Pure (tested). Values = config/drive_sim.yaml (a test checks they stay equal).

export const DRIVE_SIM = {
  tickHz: 20, // physics steps per second
  speedStepKmh: 10, // one press of accelerate / decelerate changes the target by this
  maxKmh: 120,
  accelKmhPerS: 8, // ~0-50 km/h in 6 s, an ordinary car
  brakeKmhPerS: 15, // decelerate / stop
  cruiseKmh: 50, // "c" / "Chạy đều 50"
} as const;

export type TurnSignal = "left" | "right" | null;

export interface CarState {
  speedKmh: number;
  targetKmh: number;
  turn: TurnSignal;
}

export type DriveCommand = "accelerate" | "decelerate" | "stop" | "cruise" | "left" | "right" | "signal_off";

export const PARKED: CarState = { speedKmh: 0, targetKmh: 0, turn: null };

export function command(car: CarState, cmd: DriveCommand): CarState {
  const s = DRIVE_SIM;
  switch (cmd) {
    case "accelerate":
      return { ...car, targetKmh: Math.min(car.targetKmh + s.speedStepKmh, s.maxKmh) };
    case "decelerate":
      return { ...car, targetKmh: Math.max(car.targetKmh - s.speedStepKmh, 0) };
    case "stop":
      return { ...car, targetKmh: 0 };
    case "cruise":
      return { ...car, targetKmh: s.cruiseKmh };
    case "left":
    case "right":
      return { ...car, turn: car.turn === cmd ? null : cmd }; // same side again = off
    case "signal_off":
      return { ...car, turn: null };
  }
}

export function step(car: CarState, dtS: number): CarState {
  const gap = car.targetKmh - car.speedKmh;
  if (gap === 0) return car;
  const rate = gap > 0 ? DRIVE_SIM.accelKmhPerS : DRIVE_SIM.brakeKmhPerS;
  const move = Math.min(Math.abs(gap), rate * dtS);
  return { ...car, speedKmh: car.speedKmh + Math.sign(gap) * move };
}

/** Keys of tools/drive_sim.py, so the same hands work on both. */
export const DRIVE_KEYS: Record<string, DriveCommand> = {
  w: "accelerate",
  ArrowUp: "accelerate",
  s: "decelerate",
  ArrowDown: "decelerate",
  " ": "stop",
  c: "cruise",
  a: "left",
  ArrowLeft: "left",
  d: "right",
  ArrowRight: "right",
  x: "signal_off",
};

const CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // no 0 / O / 1 / I: read aloud from a screen

/** Pairing code #/live shows and #/drive types (backend pattern ^[A-Z0-9]{6}$). */
export function newDriveCode(random: (n: number) => Uint8Array = (n) => crypto.getRandomValues(new Uint8Array(n))): string {
  return Array.from(random(6), (b) => CODE_CHARS[b % CODE_CHARS.length]).join("");
}

export function isDriveCode(code: string): boolean {
  return /^[A-Z0-9]{6}$/.test(code);
}
