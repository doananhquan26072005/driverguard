"""Block 7 - Drowsiness branch.

Per frame, from FrameFeatures (EAR, MAR, head pose), computes:
- eye_closed: per-frame eye state (None when it cannot be judged). From EAR, or from the
  eye-state CNN (block 5, `p_closed`) on frames where EAR is not reliable.
- closed_duration: seconds of the current eye-closure episode.
- perclos_60s: fraction of time the eyes were closed over the last `perclos_window_s`.
- blink_rate: blinks per minute (closures shorter than `blink_max_s`).
- yawn_count_10min, nod_count_5min: events in their windows.
and emits events ("blink", "microsleep", "yawn", "nod", "perclos_high") on the frame
they happen.

Sub-modules, each with its own anti false-positive rules in its docstring:
- eyes.py: open-eye baseline, close / reopen hysteresis, closure episodes (blinks, deep
  closure -> microsleep, head-drop carry), PERCLOS.
- mouth.py: yawns, and the yawn / talking mask on closed-eye time.
- head.py: the driver's usual head pose, nods vs bows.
- slow_blink.py: blink duration and eyelid reopening time.
- brow.py: brows raised to keep drooping eyes open.
- analyzer.py: DrowsinessAnalyzer, which runs them in order on each frame.

Pure logic on timestamps: no image, no clock, testable with fake sequences.
"""

from edge_agent.analysis.drowsiness.analyzer import DrowsinessAnalyzer, describe_events
from edge_agent.analysis.drowsiness.common import RollingWindow
from edge_agent.analysis.drowsiness.config import DrowsinessConfig, DrowsinessState

__all__ = ["DrowsinessAnalyzer", "DrowsinessConfig", "DrowsinessState", "RollingWindow", "describe_events"]
