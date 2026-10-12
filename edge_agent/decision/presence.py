"""Block 12 stage - Presence check: "Bạn còn ở đó không?" (docs/safety-fmea.md row 6).

A driver who slumps out of the camera's view without the eyes having been seen closed looks, to
block 9, like any lost face: monitoring unavailable, no alert, and nobody is told. So when the face
has been lost that way (unavailable with reason no_face: the image itself is fine, see the block 6
quality stage) for `ask_after_s` while moving, the HUD asks the driver, with a sound, to tap the
screen once. Three ways out:
- the face is seen again: the question goes away by itself;
- the driver taps (`ack`): answered, not asked again until the face has been seen again;
- no answer within `answer_s`: "no_answer", reported to the backend at once so the fleet view can
  show it while it is happening. It stays `unanswered` until the face is back or the driver taps.

A face that flickers (a cap, a mask, a camera aimed badly: one frame with a face every few seconds)
must not turn that into a question every few seconds (M74):
- once the question was asked, the face only counts as back after it has been seen for `back_s`
  without a break; a shorter glimpse leaves the question, the answer or `unanswered` as it is;
- after a tap, no new question for `reask_after_s`, even when the face came back and went again.

A covered lens, a badly aimed camera or an unusable image are camera problems, not a missing
driver: no question (the HUD names the cause instead). Pure logic on the times it is given.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from edge_agent.config import config_from_dict

NO_ANSWER = "no_answer"  # system event reason


@dataclass(frozen=True)
class PresenceConfig:
    enabled: bool = True
    ask_after_s: float = 5.0  # face lost (no_face) this long while moving: ask
    answer_s: float = 10.0  # no tap this long after asking: no_answer
    back_s: float = 1.0  # once asked, the face must be seen this long before the loss is over
    reask_after_s: float = 60.0  # no new question this long after the driver's tap

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> PresenceConfig:
        """Build the config from its section of thresholds.yaml; an unknown key is an error."""
        return config_from_dict(cls, d, "presence")


@dataclass(frozen=True)
class PresenceState:
    asking: bool = False  # the HUD shows the question now
    remaining_s: float = 0.0  # time left to answer, while asking
    unanswered: bool = False  # asked, nobody answered, the face is still gone
    event: str | None = None  # "asked", "answered" or "no_answer", on the frame it happens


class PresenceCheck:
    def __init__(self, config: PresenceConfig | None = None) -> None:
        self.config = config or PresenceConfig()
        self._lost_since: float | None = None
        self._asked_at: float | None = None
        self._answered = False  # for this loss of the face
        self._unanswered = False
        self._back_since: float | None = None  # the face has been seen again since this time
        self._last_answer: float | None = None  # time of the driver's last tap

    def _loss_over(self) -> None:
        self._lost_since = self._asked_at = self._back_since = None
        self._answered = self._unanswered = False

    def reset(self) -> None:
        """End the running loss and forget the driver's last answer."""
        self._loss_over()
        self._last_answer = None

    def update(self, t: float, lost: bool, ack: bool = False) -> PresenceState:
        """lost: monitoring is unavailable because the driver is out of view. ack: the driver tapped."""
        cfg = self.config
        if not cfg.enabled:
            return PresenceState()
        if not lost:
            touched = self._asked_at is not None or self._answered or self._unanswered
            if self._back_since is None:
                self._back_since = t
            if not touched or t - self._back_since >= cfg.back_s:
                self._loss_over()
                return PresenceState()
        else:
            self._back_since = None
        if self._lost_since is None:
            self._lost_since = t
        if ack and (self._asked_at is not None or self._unanswered) and not self._answered:
            self._answered, self._unanswered, self._asked_at = True, False, None
            self._last_answer = t
            return PresenceState(event="answered")
        if self._answered:
            return PresenceState()
        if self._unanswered:
            return PresenceState(unanswered=True)
        if self._asked_at is None:
            if t - self._lost_since < cfg.ask_after_s:
                return PresenceState()
            if self._last_answer is not None and t - self._last_answer < cfg.reask_after_s:
                return PresenceState()
            self._asked_at = t
            return PresenceState(asking=True, remaining_s=cfg.answer_s, event="asked")
        waited = t - self._asked_at
        if waited >= cfg.answer_s:
            self._asked_at, self._unanswered = None, True
            return PresenceState(unanswered=True, event=NO_ANSWER)
        return PresenceState(asking=True, remaining_s=cfg.answer_s - waited)
