"""Driving simulator: a stand-in for the vehicle's CAN bus (block 10 source), run in a terminal.

    python tools/drive_sim.py                                   # drive with the keyboard
    python tools/drive_sim.py --scenario config/scenarios/city_day.yaml   # replay a scripted drive

Keys: w / ↑ accelerate (+10 km/h target), s / ↓ decelerate (-10), space stop, c cruise 50 km/h,
a / ← left turn signal, d / → right turn signal (press again = off), x signal off, q quit.
The speed moves toward the target at a car's pace (config/drive_sim.yaml). The turn signal stays
on until it is switched off (same key again, the other side, or x).

It serves the current reading on http://127.0.0.1:<port>/can as
{"speed_kmh": 42.0, "turn_signal": "left" | "right" | null, "t": seconds since start, "source": ...}.
Both the device agent (edge_agent.main, --sim-url) and the browser agent (#/live) poll it.
Not running = no speed = the vehicle stands still at 0 km/h (parked). Only numbers, no images.
"""

from __future__ import annotations

import argparse
import json
import os
import select
import signal
import sys
import threading
import time
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.config import PROJECT_ROOT, config_from_dict  # noqa: E402
from edge_agent.context.can_sim import CanSimulator, load_scenario  # noqa: E402

DEFAULT_CONFIG = PROJECT_ROOT / "config" / "drive_sim.yaml"
TURNS = ("left", "right")


@dataclass(frozen=True)
class DriveSimConfig:
    port: int = 8766
    tick_hz: float = 20.0
    speed_step_kmh: float = 10.0
    max_kmh: float = 120.0
    accel_kmh_per_s: float = 8.0
    brake_kmh_per_s: float = 15.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> DriveSimConfig:
        """Build the config from its section of the YAML; an unknown key is an error."""
        return config_from_dict(cls, d, "drive_sim")


def load_config(path: str | Path = DEFAULT_CONFIG) -> DriveSimConfig:
    """Load the simulator's config from its YAML file."""
    with open(path, encoding="utf-8") as f:
        return DriveSimConfig.from_dict(yaml.safe_load(f))


class DriveSim:
    """The simulated car. Pure: commands change the target, step(dt) moves the speed toward it."""

    def __init__(self, cfg: DriveSimConfig | None = None) -> None:
        self.cfg = cfg or DriveSimConfig()
        self.t = 0.0
        self.speed_kmh = 0.0
        self.target_kmh = 0.0
        self.turn_signal: str | None = None

    # ------------------------------------------------------------------ commands
    def accelerate(self) -> None:
        """Raise the target speed by one step, up to `max_kmh`."""
        self.target_kmh = min(self.target_kmh + self.cfg.speed_step_kmh, self.cfg.max_kmh)

    def decelerate(self) -> None:
        """Lower the target speed by one step, down to 0."""
        self.target_kmh = max(self.target_kmh - self.cfg.speed_step_kmh, 0.0)

    def stop(self) -> None:
        """Set the target speed to 0."""
        self.target_kmh = 0.0

    def cruise(self, kmh: float) -> None:
        """Set the target speed, clamped to [0, max_kmh]."""
        self.target_kmh = min(max(kmh, 0.0), self.cfg.max_kmh)

    def signal(self, side: str | None) -> None:
        """'left' / 'right' (same side again = off) or None (off)."""
        if side is None or side == self.turn_signal:
            self.turn_signal = None
        elif side in TURNS:
            self.turn_signal = side

    # ------------------------------------------------------------------ physics
    def step(self, dt: float) -> None:
        """Advance the simulation by dt seconds: the speed moves towards its target."""
        self.t += dt
        gap = self.target_kmh - self.speed_kmh
        rate = self.cfg.accel_kmh_per_s if gap > 0 else self.cfg.brake_kmh_per_s
        move = min(abs(gap), rate * dt)
        self.speed_kmh += move if gap > 0 else -move

    def reading(self) -> dict[str, Any]:
        """The current reading (speed_kmh, turn_signal, t) as served on /can."""
        return {"speed_kmh": round(self.speed_kmh, 1), "turn_signal": self.turn_signal, "t": round(self.t, 2)}


class ScenarioDrive:
    """Replays a CAN scenario (config/scenarios/*.yaml) instead of the keyboard."""

    def __init__(self, path: str | Path) -> None:
        self.can = CanSimulator(load_scenario(path))
        self.t = 0.0
        self._last = self.can.sample(0.0)

    def step(self, dt: float) -> None:
        """Advance the scenario by dt seconds."""
        self.t += dt
        self._last = self.can.sample(self.t)

    def reading(self) -> dict[str, Any]:
        """The current reading (speed_kmh, turn_signal, t) as served on /can."""
        speed = self._last.speed_kmh or 0.0
        return {"speed_kmh": round(speed, 1), "turn_signal": self._last.turn_signal, "t": round(self.t, 2)}


KEYS = {
    "w": "accelerate",
    "\x1b[A": "accelerate",
    "s": "decelerate",
    "\x1b[B": "decelerate",
    " ": "stop",
    "c": "cruise",
    "a": "left",
    "\x1b[D": "left",
    "d": "right",
    "\x1b[C": "right",
    "x": "signal_off",
    "q": "quit",
}


def apply_key(sim: DriveSim, key: str) -> bool:
    """One key press; False = quit."""
    action = KEYS.get(key.lower() if len(key) == 1 else key)
    if action == "quit":
        return False
    if action in ("accelerate", "decelerate", "stop"):
        getattr(sim, action)()
    elif action == "cruise":
        sim.cruise(50.0)
    elif action in TURNS:
        sim.signal(action)
    elif action == "signal_off":
        sim.signal(None)
    return True


# ---------------------------------------------------------------------- HTTP: GET /can
class SimServer:
    """127.0.0.1 only. Any origin may read it (speed numbers, nothing private), including the
    hosted #/live page: Chrome's private-network preflight is answered."""

    def __init__(self, source: Any, source_name: str, port: int, lock: threading.Lock) -> None:
        def read() -> dict[str, Any]:
            with lock:
                return {**source.reading(), "source": source_name}

        class Handler(BaseHTTPRequestHandler):
            server_version = "DriverGuardDriveSim/1"

            def log_message(self, fmt: str, *args: Any) -> None:  # the terminal shows the car
                """No access log: the terminal shows the car."""
                pass

            def _headers(self) -> None:
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                if self.headers.get("Access-Control-Request-Private-Network") == "true":
                    self.send_header("Access-Control-Allow-Private-Network", "true")

            def do_OPTIONS(self) -> None:  # noqa: N802 - http.server naming
                """CORS preflight."""
                self.send_response(204)
                self._headers()
                self.end_headers()

            def do_GET(self) -> None:  # noqa: N802
                """GET /can: the current reading as JSON."""
                if self.path.split("?")[0] != "/can":
                    self.send_response(404)
                    self._headers()
                    self.end_headers()
                    return
                data = json.dumps(read()).encode()
                self.send_response(200)
                self._headers()
                self.send_header("Content-Type", "application/json")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.httpd.daemon_threads = True
        self.port = self.httpd.server_address[1]
        self._thread = threading.Thread(target=self.httpd.serve_forever, name="DriveSimServer", daemon=True)

    def start(self) -> SimServer:
        """Serve on a background thread."""
        self._thread.start()
        return self

    def stop(self) -> None:
        """Stop serving and close the socket."""
        self.httpd.shutdown()
        self.httpd.server_close()


# ---------------------------------------------------------------------- terminal
def _status(r: dict[str, Any], target: float | None) -> str:
    turn = {"left": "◀◀ XI NHAN TRÁI", "right": "XI NHAN PHẢI ▶▶"}.get(r["turn_signal"] or "", "")
    state = "ĐỖ / DỪNG" if r["speed_kmh"] < 1.0 else "ĐANG LÁI"
    goal = "" if target is None else f" (mục tiêu {target:.0f})"
    return f"\r{r['speed_kmh']:6.1f} km/h{goal:16s} {state:10s} {turn:16s}"


def _read_keys(fd: int) -> list[str]:
    keys: list[str] = []
    while select.select([fd], [], [], 0)[0]:
        data = os.read(fd, 16).decode(errors="ignore")
        i = 0
        while i < len(data):
            if data[i] == "\x1b" and data[i + 1 : i + 2] == "[" and i + 2 < len(data):
                keys.append(data[i : i + 3])
                i += 3
            else:
                keys.append(data[i])
                i += 1
    return keys


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point (see the module doc). Returns the process exit code."""
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--port", type=int, default=None, help="override the port of the config")
    p.add_argument("--scenario", default=None, help="replay a CAN scenario YAML instead of the keyboard")
    args = p.parse_args(argv)
    signal.signal(signal.SIGTERM, lambda *_: (_ for _ in ()).throw(KeyboardInterrupt))  # kill = clean stop

    cfg = load_config(args.config)
    source: DriveSim | ScenarioDrive
    if args.scenario:
        source, name = ScenarioDrive(args.scenario), Path(args.scenario).stem
    else:
        source, name = DriveSim(cfg), "keyboard"
    lock = threading.Lock()
    server = SimServer(source, name, args.port or cfg.port, lock).start()
    print(f"[drive_sim] http://127.0.0.1:{server.port}/can ({name})")
    if isinstance(source, DriveSim):
        print(
            "  w/↑ tăng tốc  s/↓ giảm tốc  space dừng  c chạy 50 km/h  a/← xi nhan trái  d/→ xi nhan phải  x tắt  q thoát"
        )
    else:
        print("  replaying the scenario, q / Ctrl+C to quit")

    interactive = sys.stdin.isatty()
    fd = sys.stdin.fileno()
    old = None
    if interactive:
        import termios
        import tty

        old = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    dt = 1.0 / cfg.tick_hz
    try:
        running = True
        last = time.monotonic()
        while running:
            time.sleep(dt)
            now = time.monotonic()
            with lock:
                if interactive:
                    for key in _read_keys(fd):
                        if key.lower() == "q":
                            running = False
                        elif isinstance(source, DriveSim):
                            apply_key(source, key)
                source.step(now - last)
                reading = source.reading()
            last = now
            target = source.target_kmh if isinstance(source, DriveSim) else None
            sys.stdout.write(_status(reading, target))
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
    finally:
        if old is not None:
            import termios

            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        server.stop()
        print("\n[drive_sim] stopped: the agents now see 0 km/h (parked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
