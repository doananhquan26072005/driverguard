// #/drive?code=XXXXXX: the web driving controls (M31). A remote for the simulated car of a #/live
// session, usually on another device (a phone next to the laptop running #/live): speed up / slow
// down / stop / cruise 50, turn signals. The car moves at a car's pace (sim.ts, as
// tools/drive_sim.py) and its speed / turn signal go to the backend under the pairing code #/live
// shows; #/live reads them. Numbers only. Closing this page while driving reads as a lost vehicle
// signal on #/live (M26).
import { Gauge, Unplug } from "lucide-react";
import { useEffect, useState } from "react";
import { API_URL } from "../lib/api";
import { DRIVE_SIM, isDriveCode } from "./sim";
import { DEFAULTS } from "../lib/defaults";
import { steadyInterval } from "../lib/ticker";
import DrivePanel from "./DrivePanel";
import { useCar } from "./useCar";

// context.vehicle_send_s: below context.vehicle_signal_stale_s, after which #/live treats a reading as lost.
const SEND_MS = DEFAULTS.vehicle.send_s * 1000;

function codeFromHash(): string {
  const q = new URLSearchParams(window.location.hash.split("?")[1] ?? "");
  return (q.get("code") ?? "").toUpperCase();
}

type Link = "idle" | "ok" | "error";

export default function DriveScreen() {
  const [code, setCode] = useState(codeFromHash);
  const [draft, setDraft] = useState(code);
  const { car, carRef, act } = useCar({ keys: true });
  const [link, setLink] = useState<Link>("idle");
  const paired = isDriveCode(code);

  // Send the current reading.
  useEffect(() => {
    if (!paired) return;
    let busy = false;
    return steadyInterval(async () => {
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
  }, [code, paired, carRef]);

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
            <DrivePanel
              car={car}
              act={act}
              status={
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
              }
            />

            <p className="m-0 text-hud-label text-hud-ink-3">
              Phím: W / ↑ tăng, S / ↓ giảm, Space dừng, C chạy đều {DRIVE_SIM.cruiseKmh}, A / ← trái, D / → phải, X tắt
              xi nhan. Đóng trang này khi xe đang chạy thì trang giám sát báo "Mất tín hiệu tốc độ xe".
            </p>
          </>
        )}
      </main>
    </div>
  );
}
