"""Web driving controls (M31): #/drive sets the simulated speed / turn signal, #/live reads them.

Two browsers (often two devices: a phone as the remote, a laptop running #/live) cannot talk to
each other directly, so the backend relays the latest reading under a short pairing code that
#/live shows. Numbers only (speed, turn signal), kept in memory, never written to the database:
a code expires `ttl_s` after its last update, and at most `max_codes` live at once (oldest dropped).
#/live only uses a reading younger than the vehicle's stale time, so a closed remote page reads as a
lost vehicle signal (M26).
"""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DriveReading:
    speed_kmh: float
    turn_signal: str | None
    age_s: float


class DriveLinks:
    def __init__(self, ttl_s: float = 600.0, max_codes: int = 500, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_s, self.max_codes, self._clock = ttl_s, max_codes, clock
        self._lock = threading.Lock()
        self._codes: OrderedDict[str, tuple[float, str | None, float]] = OrderedDict()  # code -> speed, turn, at

    def put(self, code: str, speed_kmh: float, turn_signal: str | None) -> None:
        with self._lock:
            self._codes.pop(code, None)
            self._codes[code] = (speed_kmh, turn_signal, self._clock())
            while len(self._codes) > self.max_codes:
                self._codes.popitem(last=False)

    def get(self, code: str) -> DriveReading | None:
        with self._lock:
            item = self._codes.get(code)
            if item is None:
                return None
            speed, turn, at = item
            age = self._clock() - at
            if age > self.ttl_s:
                del self._codes[code]
                return None
            return DriveReading(speed, turn, age)
