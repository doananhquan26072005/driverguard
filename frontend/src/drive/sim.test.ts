import { describe, expect, it } from "vitest";
import driveSimYaml from "../../../config/drive_sim.yaml?raw";
import { command, DRIVE_KEYS, DRIVE_SIM, isDriveCode, newDriveCode, PARKED, step } from "./sim";

function run(car: typeof PARKED, seconds: number) {
  let c = car;
  for (let i = 0; i < seconds * DRIVE_SIM.tickHz; i++) c = step(c, 1 / DRIVE_SIM.tickHz);
  return c;
}

describe("web driving controls (M31)", () => {
  it("uses the same car as tools/drive_sim.py (config/drive_sim.yaml)", () => {
    const yaml = driveSimYaml;
    const num = (key: string) => Number(new RegExp(`^${key}:\\s*([0-9.]+)`, "m").exec(yaml)?.[1]);
    expect(DRIVE_SIM.tickHz).toBe(num("tick_hz"));
    expect(DRIVE_SIM.speedStepKmh).toBe(num("speed_step_kmh"));
    expect(DRIVE_SIM.maxKmh).toBe(num("max_kmh"));
    expect(DRIVE_SIM.accelKmhPerS).toBe(num("accel_kmh_per_s"));
    expect(DRIVE_SIM.brakeKmhPerS).toBe(num("brake_kmh_per_s"));
  });

  it("speeds up and brakes at a car's pace", () => {
    let car = command(PARKED, "cruise");
    expect(car.targetKmh).toBe(50);
    expect(run(car, 3).speedKmh).toBeCloseTo(24, 5); // 8 km/h per s
    car = run(car, 10);
    expect(car.speedKmh).toBe(50);
    car = run(command(car, "stop"), 2);
    expect(car.speedKmh).toBeCloseTo(20, 5); // 15 km/h per s
    expect(run(car, 5).speedKmh).toBe(0);
  });

  it("steps the target by 10 between 0 and the maximum", () => {
    let car = PARKED;
    for (let i = 0; i < 20; i++) car = command(car, "accelerate");
    expect(car.targetKmh).toBe(DRIVE_SIM.maxKmh);
    for (let i = 0; i < 20; i++) car = command(car, "decelerate");
    expect(car.targetKmh).toBe(0);
  });

  it("toggles the turn signal like the terminal tool", () => {
    let car = command(PARKED, "left");
    expect(car.turn).toBe("left");
    expect(command(car, "left").turn).toBeNull(); // same side again = off
    car = command(car, "right");
    expect(car.turn).toBe("right");
    expect(command(car, "signal_off").turn).toBeNull();
    expect(DRIVE_KEYS[" "]).toBe("stop");
  });

  it("makes pairing codes the backend accepts", () => {
    const code = newDriveCode((n) => new Uint8Array(n).map((_, i) => i * 7));
    expect(isDriveCode(code)).toBe(true);
    expect(code).not.toMatch(/[01IO]/);
    expect(isDriveCode("abc123")).toBe(false);
  });
});
