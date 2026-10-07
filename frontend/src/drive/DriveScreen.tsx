// #/drive?code=XXXXXX: the web driving controls (M31). A remote for the simulated car of a #/live
// session, usually on another device (a phone next to the laptop running #/live): speed up / slow
// down / stop / cruise 50, turn signals. The car moves at a car's pace (sim.ts, as
// tools/drive_sim.py) and its speed / turn signal go to the backend under the pairing code #/live
// shows; #/live reads them. Numbers only. Closing this page while driving reads as a lost vehicle
// signal on #/live (M26).
import { ArrowBigLeft, ArrowBigRight, ChevronDown, ChevronUp, Gauge, OctagonX, Unplug } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { API_URL } from "../lib/api";
import { command, DRIVE_KEYS, DRIVE_SIM, type DriveCommand, isDriveCode, PARKED, step } from "./sim";

const SEND_MS = 200; // #/live reads every 250 ms and treats a reading older than 1 s as lost

function codeFromHash(): string {
  const q = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return (q.get("code") ?? "").toUpperCase();
}

type Link = "idle" | "ok" | "error";

export default function DriveScreen() {
  const [code, setCode] = useState(codeFromHash);
  const [draft, setDraft] = useState(code);
  const [car, setCar] = useState(PARKED);
  const [link, setLink] = useState<Link>("idle");
  const carRef = useRef(car);
  carRef.current = car;
  const paired = isDriveCode(code);

  // Physics at tick_hz.
  useEffect(() => {
    const dt = 1 / DRIVE_SIM.tickHz;
    const id = setInterval(() => setCar((c) => step(c, dt)), dt * 1000);
    return () => clearInterval(id);
  }, []);

  // Send the current reading.
  useEffect(() => {
    if (!paired) return;
    let busy = false;
    const id = setInterval(async () => {
      if (busy) return;
      busy = true;
      const c = carRef.current;
      try {
        const resp = await fetch(`${API_URL}/api/v1/drive/${code}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ speed_kmh: Math.round(c.speedKmh * 10) / 10, turn_signal: c.turn }),
          signal: AbortSignal.timeout(SEND_MS * 4),
        });
        setLink(resp.ok ? "ok" : "error");
      } catch {
        setLink("error");
      } finally {
        busy = false;
      }
    }, SEND_MS);
    return () => clearInterval(id);
  }, [code, paired]);

  const act = useCallback((cmd: DriveCommand) => setCar((c) => command(c, cmd)), []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      const cmd = DRIVE_KEYS[e.key];
      if (!cmd) return;
      e.preventDefault();
      act(cmd);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [act]);

  const pair = () => {
    const c = draft.trim().toUpperCase();
    if (!isDriveCode(c)) return;
    setCode(c);
    window.location.hash = `#/drive?code=${c}`;
  };

  const btn =
    "inline-flex min-h-20 items-center justify-center gap-2 rounded-hud-sm border-0 px-4 text-hud-title font-semibold ring-1 transition active:scale-[0.98]";

  return (
    <div className="live-setup block font-hud text-hud-ink antialiased [color-scheme:dark]">
      <main className="mx-auto grid max-w-xl gap-5 px-4 py-6">
        <header className="flex items-center gap-2">
          <Gauge aria-hidden className="size-6 text-hud-system" />
          <h1 className="m-0 text-hud-title font-bold">Điều khiển xe</h1>
          {paired && (
            <span className="ml-auto dg-chip !text-[15px] tabular-nums">
              Mã {code}
            </span>
          )}
        </header>

        {!paired ? (
          <section className="grid gap-3 dg-card p-5">
            <p className="m-0 text-hud-body text-hud-ink-2">
              Nhập mã 6 ký tự hiện ở góc camera của trang giám sát <code>#/live</code>.
            </p>
            <div className="flex gap-2">
              <input
                aria-label="Mã ghép"
                value={draft}
                onChange={(e) => setDraft(e.target.value.toUpperCase())}
                onKeyDown={(e) => e.key === "Enter" && pair()}
                maxLength={6}
                className="min-h-14 flex-1 rounded-hud-sm border border-solid border-white/14 bg-white/4 px-4 text-hud-title font-semibold tracking-[0.3em] text-hud-ink uppercase"
              />
              <button type="button" onClick={pair} disabled={!isDriveCode(draft.trim().toUpperCase())} className={`${btn} min-h-14 bg-[linear-gradient(180deg,#93c5fd_0%,#60a5fa_100%)] text-[#0b1b33] ring-transparent disabled:opacity-40`}>
                Ghép
              </button>
            </div>
          </section>
        ) : (
          <>
            <section aria-label="Tốc độ" className="grid justify-items-center gap-1 dg-card p-5">
              <div className="flex items-center gap-6">
                <ArrowBigLeft aria-label={`Xi nhan trái: ${car.turn === "left" ? "bật" : "tắt"}`} role="img" className={`size-14 ${car.turn === "left" ? "fill-hud-turn text-hud-turn animate-hud-blink motion-reduce:animate-none" : "text-hud-ink-3 opacity-40"}`} />
                <span className="text-[clamp(56px,14vw,96px)] leading-none font-semibold tracking-[-0.03em] tabular-nums">{Math.round(car.speedKmh)}</span>
                <ArrowBigRight aria-label={`Xi nhan phải: ${car.turn === "right" ? "bật" : "tắt"}`} role="img" className={`size-14 ${car.turn === "right" ? "fill-hud-turn text-hud-turn animate-hud-blink motion-reduce:animate-none" : "text-hud-ink-3 opacity-40"}`} />
              </div>
              <span className="text-hud-body text-hud-ink-2">km/h · mục tiêu {car.targetKmh}</span>
              <span role="status" className={`text-hud-label ${link === "error" ? "text-hud-caution" : "text-hud-ink-3"}`}>
                {link === "error" ? (
                  <span className="inline-flex items-center gap-1">
                    <Unplug aria-hidden className="size-4" /> Không gửi được tới máy chủ, đang thử lại
                  </span>
                ) : link === "ok" ? (
                  "Đang gửi cho trang giám sát"
                ) : (
                  "Đang kết nối…"
                )}
              </span>
            </section>

            <section aria-label="Tốc độ" className="grid grid-cols-2 gap-3">
              <button type="button" onClick={() => act("accelerate")} className={`${btn} dg-tile text-hud-ink ring-transparent`}>
                <ChevronUp aria-hidden className="size-7" /> Tăng tốc
              </button>
              <button type="button" onClick={() => act("decelerate")} className={`${btn} dg-tile text-hud-ink ring-transparent`}>
                <ChevronDown aria-hidden className="size-7" /> Giảm tốc
              </button>
              <button type="button" onClick={() => act("cruise")} className={`${btn} dg-tile text-hud-ink ring-transparent`}>
                Chạy đều {DRIVE_SIM.cruiseKmh}
              </button>
              <button type="button" onClick={() => act("stop")} className={`${btn} bg-hud-danger text-white ring-transparent`}>
                <OctagonX aria-hidden className="size-7" /> Dừng xe
              </button>
            </section>

            <section aria-label="Xi nhan" className="grid grid-cols-3 gap-3">
              <button type="button" aria-pressed={car.turn === "left"} onClick={() => act("left")} className={`${btn} ${car.turn === "left" ? "bg-hud-turn text-hud-on-warning ring-transparent" : "dg-tile text-hud-ink ring-transparent"}`}>
                <ArrowBigLeft aria-hidden className="size-7" /> Trái
              </button>
              <button type="button" onClick={() => act("signal_off")} className={`${btn} dg-tile text-hud-ink-2 ring-transparent`}>
                Tắt
              </button>
              <button type="button" aria-pressed={car.turn === "right"} onClick={() => act("right")} className={`${btn} ${car.turn === "right" ? "bg-hud-turn text-hud-on-warning ring-transparent" : "dg-tile text-hud-ink ring-transparent"}`}>
                Phải <ArrowBigRight aria-hidden className="size-7" />
              </button>
            </section>

            <p className="m-0 text-hud-label text-hud-ink-3">
              Phím: W / ↑ tăng, S / ↓ giảm, Space dừng, C chạy đều {DRIVE_SIM.cruiseKmh}, A / ← trái, D / → phải, X tắt
              xi nhan. Đóng trang này khi xe đang chạy thì trang giám sát báo "Mất tín hiệu xe".
            </p>
          </>
        )}
      </main>
    </div>
  );
}
