"""Evaluation metrics shared by tools/eval.py and tools/seq_eval.py. Pure functions, no video.

Two kinds of numbers, answering two questions (docs/improvements.md, section 2):

- False alarms per hour: how often an awake driver is disturbed for nothing (the PRD target is
  ≤ 1.0 / h). Always printed with the hours it is measured on and an exact Poisson 95 % CI,
  because a few false alarms on a few minutes of video say little (1 in 26 min = 2.3 / h, CI
  0.06 – 12.9). The hours are those where a false alarm can happen at all: the video time minus
  the labelled episodes the predictions are matched against (widened by the match tolerance).
- FAR / MAR on fixed windows (`window_scores`): the share of awake windows the system calls
  drowsy, and of drowsy windows it misses (late detection counts as a miss). Windows, not
  frames: at 30 fps neighbouring frames are near copies, so a frame-level FAR looks far more
  precise than it is. Printed with a Wilson 95 % CI; windows of one clip are still correlated,
  so that CI is optimistic.

Window rules (config/thresholds.yaml, section `eval`):
- windows of `window_s`, not overlapping, from `warmup_s` on (the start-up stretch, before the
  driver's baselines and the PERCLOS window fill up, is left out and reported apart);
- drowsy window: at least `positive_frac` of it inside a labelled drowsy episode;
  awake window: at least `positive_frac` of it inside known-awake time and not touching a drowsy
  episode (widened by the tolerance); any other window (on a border, unlabelled) is skipped;
- predicted drowsy: the drowsiness branch's risk level reaches `min_level` somewhere in the
  window. Distraction (off_road, phone) is scored on its own, never mixed into drowsiness.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Any

from edge_agent.config import config_from_dict

DROWSY_REASONS = ("microsleep", "drowsy_score", "trend", "blink_rate")
DISTRACTION_REASONS = ("off_road", "phone")

Interval = tuple[float, float]


@dataclass(frozen=True)
class EvalConfig:
    window_s: float = 10.0
    warmup_s: float = 30.0
    positive_frac: float = 0.5
    min_level: int = 1
    # Own recordings (tools/record_trace.py): a key-press label is matched this far on both sides.
    label_tolerance_s: float = 1.0
    # tools/trace_studies.py: face-brightness bin edges (0-255), and how much of an awake clip stands
    # in for driver enrollment.
    brightness_bins: tuple[float, ...] = (60.0, 100.0, 140.0)
    fake_enroll_s: float = 10.0
    # tools/light_study.py: the same videos darkened (gamma), overexposed (gain), blurred (sigma in
    # pixels at 640 px width) in RAM.
    light_gammas: tuple[float, ...] = (1.5, 2.2, 3.5, 5.0)
    light_gains: tuple[float, ...] = (1.5, 2.5, 4.0)
    light_blur_sigmas: tuple[float, ...] = (1.5, 3.0, 6.0)
    # tools/benchmark.py --duration: what a long run has to keep up.
    soak_min_fps: float = 15.0
    soak_rss_growth_mb_per_h: float = 20.0

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> EvalConfig:
        return config_from_dict(cls, d, "eval")


# --------------------------------------------------------------------------- confidence intervals


def _poisson_cdf(k: int, mu: float) -> float:
    """P(X <= k) for X ~ Poisson(mu), summed in log space (fine for the counts we have)."""
    if mu <= 0:
        return 1.0
    total, term = 0.0, -mu  # log of the k = 0 term
    for i in range(k + 1):
        if i:
            term += math.log(mu) - math.log(i)
        total += math.exp(term)
    return min(total, 1.0)


def _solve(f: Any, target: float, lo: float, hi: float) -> float:
    """mu in [lo, hi] with f(mu) = target, f decreasing in mu (bisection)."""
    for _ in range(200):
        mid = (lo + hi) / 2
        if f(mid) > target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def poisson_ci(k: int, conf: float = 0.95) -> tuple[float, float]:
    """Exact (Garwood) CI of a Poisson count k: the mean count, not yet divided by the exposure."""
    a = 1.0 - conf
    upper_bound = max(10.0, 3.0 * k + 30.0)
    hi = _solve(lambda mu: _poisson_cdf(k, mu), a / 2, 0.0, upper_bound)
    lo = 0.0 if k == 0 else _solve(lambda mu: _poisson_cdf(k - 1, mu), 1 - a / 2, 0.0, upper_bound)
    return lo, hi


def rate_ci(k: int, hours: float, conf: float = 0.95) -> tuple[float | None, float | None, float | None]:
    """(rate, low, high) per hour; None without exposure."""
    if hours <= 0:
        return None, None, None
    lo, hi = poisson_ci(k, conf)
    return k / hours, lo / hours, hi / hours


def wilson_ci(k: int, n: int, z: float = 1.959964) -> tuple[float | None, float | None, float | None]:
    """(proportion, low, high) with the Wilson score interval; None when n = 0."""
    if n <= 0:
        return None, None, None
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


# --------------------------------------------------------------------------- time arithmetic


def union_length(intervals: Iterable[Interval], lo: float, hi: float) -> float:
    """Length of the union of the intervals, clipped to [lo, hi]."""
    clipped = sorted((max(a, lo), min(b, hi)) for a, b in intervals if b > lo and a < hi)
    total, end = 0.0, lo
    for a, b in clipped:
        if b <= end:
            continue
        total += b - max(a, end)
        end = b
    return total


def widen(intervals: Iterable[Interval], by: float) -> list[Interval]:
    return [(a - by, b + by) for a, b in intervals]


def exposure_seconds(duration_s: float, excluded: Iterable[Interval]) -> float:
    """Time of one video where a false alarm can happen: its duration minus the excluded episodes."""
    return max(0.0, duration_s - union_length(excluded, 0.0, duration_s))


# --------------------------------------------------------------------------- window FAR / MAR


@dataclass
class WindowCounts:
    false_alarms: int = 0  # awake windows predicted drowsy
    awake: int = 0
    misses: int = 0  # drowsy windows not predicted drowsy
    drowsy: int = 0
    skipped: int = 0  # border / unlabelled windows
    warmup_s: float = 0.0  # seconds left out at the clip starts

    def __iadd__(self, other: WindowCounts) -> WindowCounts:
        for f in ("false_alarms", "awake", "misses", "drowsy", "skipped", "warmup_s"):
            setattr(self, f, getattr(self, f) + getattr(other, f))
        return self

    @property
    def far(self) -> tuple[float | None, float | None, float | None]:
        return wilson_ci(self.false_alarms, self.awake)

    @property
    def mar(self) -> tuple[float | None, float | None, float | None]:
        return wilson_ci(self.misses, self.drowsy)


def window_scores(
    duration_s: float,
    positive: Sequence[Interval],
    awake: Sequence[Interval],
    level_per_second: Sequence[int],
    cfg: EvalConfig,
    tolerance_s: float = 0.0,
) -> WindowCounts:
    """FAR / MAR window counts of one video (see module doc).

    positive: labelled drowsy episodes; awake: time known to be awake (for a video labelled only
    with drowsy episodes, [(0, duration)]); level_per_second[i]: highest level of the scored branch
    during second i of the video.
    """
    out = WindowCounts(warmup_s=min(cfg.warmup_s, duration_s))
    near = widen(positive, tolerance_s)
    w, need = cfg.window_s, cfg.positive_frac * cfg.window_s
    start = cfg.warmup_s
    while start + w <= duration_s + 1e-9:
        end = start + w
        seconds = level_per_second[int(start) : max(int(math.ceil(end)), int(start) + 1)]
        predicted = max(seconds, default=0) >= cfg.min_level
        if union_length(positive, start, end) >= need:
            out.drowsy += 1
            out.misses += not predicted
        elif union_length(near, start, end) == 0 and union_length(awake, start, end) >= need:
            out.awake += 1
            out.false_alarms += predicted
        else:
            out.skipped += 1
        start = end
    return out


def per_second_max(times_s: Sequence[float], levels: Sequence[int], duration_s: float) -> list[int]:
    """Frame levels -> the highest level of each second of the video."""
    out = [0] * max(int(math.ceil(duration_s)), 1)
    for t, lv in zip(times_s, levels, strict=True):
        i = min(max(int(t), 0), len(out) - 1)
        if lv > out[i]:
            out[i] = int(lv)
    return out


def branch_level(hits: Iterable[Any], reasons: Sequence[str]) -> int:
    """Highest level among a RiskAssessment's hits whose reason belongs to one branch."""
    return max((h.level for h in hits if h.reason in reasons), default=0)


# --------------------------------------------------------------------------- text


def pct(v: float | None, digits: int = 1) -> str:
    return "–" if v is None else f"{v * 100:.{digits}f}%"


def ci_text(est: tuple[float | None, float | None, float | None], percent: bool = False) -> str:
    """'2.3 (0.06–12.9)' or '1.2% (0.4–3.1%)'; '–' when undefined."""
    v, lo, hi = est
    if v is None:
        return "–"
    if percent:
        return f"{pct(v)} ({pct(lo)}–{pct(hi)})"
    return f"{v:.1f} ({lo:.2f}–{hi:.1f})"


def window_table(rows: Sequence[tuple[str, WindowCounts]], cfg: EvalConfig) -> list[str]:
    """Markdown table of FAR / MAR per row, with the conventions written under it."""
    lines = [
        "| Scored | Awake windows | FAR (95% CI) | Drowsy windows | MAR (95% CI) | Skipped |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, c in rows:
        lines.append(
            f"| {name} | {c.awake} | {ci_text(c.far, True)} | {c.drowsy} | {ci_text(c.mar, True)} | {c.skipped} |"
        )
    lines += [
        "",
        f"Windows of {cfg.window_s:g} s, not overlapping, from {cfg.warmup_s:g} s after each clip start (the "
        "start-up stretch is left out). Drowsy window: ≥ "
        f"{cfg.positive_frac:.0%} inside a labelled episode; awake window: ≥ {cfg.positive_frac:.0%} known-awake and "
        "not touching an episode; others skipped. Predicted: the branch's risk level reaches the stated level in "
        "the window. Wilson CI; windows of one clip are correlated, so the CI is optimistic.",
    ]
    return lines
