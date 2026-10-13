// The driving controls (speed, turn signals) of the simulated car, drawn by #/drive (full page) and by
// the panel beside the HUD on #/live (M103, `side`). Only the picture: the car is useCar's.
import { ArrowBigLeft, ArrowBigRight, ChevronDown, ChevronUp, OctagonX } from "lucide-react";
import type { ReactNode } from "react";
import { DRIVE_SIM, type CarState, type DriveCommand } from "./sim";

interface Props {
  car: CarState;
  act: (cmd: DriveCommand) => void;
  /** Under the speed: where the reading goes. */
  status: ReactNode;
  /** The narrow column of #/live: smaller buttons and numbers. */
  side?: boolean;
}

export default function DrivePanel({ car, act, status, side = false }: Props) {
  const btn = `inline-flex items-center justify-center gap-2 rounded-hud-sm border-0 font-semibold ring-1 transition active:scale-[0.98] ${
    side ? "min-h-14 px-3 text-[18px]" : "min-h-20 px-4 text-hud-title"
  }`;
  const icon = side ? "size-6" : "size-7";
  const arrow = side ? "size-11" : "size-14";
  return (
    <>
      <section aria-label="Tốc độ" className={`grid justify-items-center gap-1 dg-card ${side ? "p-3" : "p-5"}`}>
        <div className={`flex items-center ${side ? "gap-4" : "gap-6"}`}>
          <ArrowBigLeft aria-label={`Xi nhan trái: ${car.turn === "left" ? "bật" : "tắt"}`} role="img" className={`${arrow} ${car.turn === "left" ? "fill-hud-turn text-hud-turn animate-hud-blink motion-reduce:animate-none" : "text-hud-ink-3 opacity-40"}`} />
          <span className={`leading-none font-semibold tracking-[-0.03em] tabular-nums ${side ? "text-[56px]" : "text-[clamp(56px,14vw,96px)]"}`}>{Math.round(car.speedKmh)}</span>
          <ArrowBigRight aria-label={`Xi nhan phải: ${car.turn === "right" ? "bật" : "tắt"}`} role="img" className={`${arrow} ${car.turn === "right" ? "fill-hud-turn text-hud-turn animate-hud-blink motion-reduce:animate-none" : "text-hud-ink-3 opacity-40"}`} />
        </div>
        <span className={side ? "text-[17px] text-hud-ink-2" : "text-hud-body text-hud-ink-2"}>km/h · mục tiêu {car.targetKmh}</span>
        {status}
      </section>

      <section aria-label="Tăng giảm tốc" className={`grid grid-cols-2 ${side ? "gap-2.5" : "gap-3"}`}>
        <button type="button" onClick={() => act("accelerate")} className={`${btn} dg-tile text-hud-ink ring-transparent`}>
          <ChevronUp aria-hidden className={icon} /> Tăng tốc
        </button>
        <button type="button" onClick={() => act("decelerate")} className={`${btn} dg-tile text-hud-ink ring-transparent`}>
          <ChevronDown aria-hidden className={icon} /> Giảm tốc
        </button>
        <button type="button" onClick={() => act("cruise")} className={`${btn} dg-tile text-hud-ink ring-transparent`}>
          Chạy đều {DRIVE_SIM.cruiseKmh}
        </button>
        <button type="button" onClick={() => act("stop")} className={`${btn} bg-hud-danger text-white ring-transparent`}>
          <OctagonX aria-hidden className={icon} /> Dừng xe
        </button>
      </section>

      <section aria-label="Xi nhan" className={`grid grid-cols-3 ${side ? "gap-2.5" : "gap-3"}`}>
        <button type="button" aria-pressed={car.turn === "left"} onClick={() => act("left")} className={`${btn} ${car.turn === "left" ? "bg-hud-turn text-hud-on-warning ring-transparent" : "dg-tile text-hud-ink ring-transparent"}`}>
          <ArrowBigLeft aria-hidden className={icon} /> Trái
        </button>
        <button type="button" onClick={() => act("signal_off")} className={`${btn} dg-tile text-hud-ink-2 ring-transparent`}>
          Tắt
        </button>
        <button type="button" aria-pressed={car.turn === "right"} onClick={() => act("right")} className={`${btn} ${car.turn === "right" ? "bg-hud-turn text-hud-on-warning ring-transparent" : "dg-tile text-hud-ink ring-transparent"}`}>
          Phải <ArrowBigRight aria-hidden className={icon} />
        </button>
      </section>
    </>
  );
}
