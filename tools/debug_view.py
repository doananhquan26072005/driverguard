"""Debug viewer for M0: capture (block 1) + preprocessing (block 2).

Shows the preprocessed stream in a window with FPS, brightness and IR flag.
Display only - frames are never written to disk.

    python tools/debug_view.py --source 0                # webcam
    python tools/debug_view.py --source path/to/video.mp4 --loop

Keys: q / ESC quit, r toggle raw vs processed, s toggle side-by-side, space pause.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.capture import CaptureConfig, FrameSource  # noqa: E402
from edge_agent.config import load_thresholds  # noqa: E402
from edge_agent.perception import PreprocessConfig, Preprocessor  # noqa: E402

WINDOW = "DriverGuard debug (M0)"


def to_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2 or image.shape[2] == 1:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image


def draw_overlay(image: np.ndarray, lines: list[str]) -> None:
    for i, text in enumerate(lines):
        y = 22 + i * 22
        cv2.putText(image, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 3, cv2.LINE_AA)
        cv2.putText(image, text, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 1, cv2.LINE_AA)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="0", help="camera index (e.g. 0) or video file path")
    parser.add_argument("--loop", action="store_true", help="loop the video file")
    parser.add_argument("--config", default=None, help="path to thresholds.yaml")
    args = parser.parse_args()

    thresholds = load_thresholds(args.config)
    preprocessor = Preprocessor(PreprocessConfig.from_dict(thresholds.get("preprocess")))
    source = FrameSource(args.source, CaptureConfig.from_dict(thresholds.get("capture")), loop=args.loop)

    show_raw = False
    side_by_side = False
    paused = False
    fps = 0.0
    last_t = time.monotonic()
    shown = None

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    with source:
        print(f"Source: {args.source}  camera={source.is_camera}  source_fps={source.source_fps:.1f}")
        while True:
            if not paused:
                frame = source.read(timeout=2.0)
                if frame is None:
                    if source.ended:
                        print("End of stream.")
                        break
                    continue

                t0 = time.perf_counter()
                pre = preprocessor(frame)
                pre_ms = (time.perf_counter() - t0) * 1000.0

                now = time.monotonic()
                dt = now - last_t
                last_t = now
                if dt > 0:
                    fps = 1.0 / dt if fps == 0 else 0.9 * fps + 0.1 / dt

                raw = to_bgr(frame.image)
                if pre.scale != 1.0:
                    raw = cv2.resize(raw, (pre.image.shape[1], pre.image.shape[0]), interpolation=cv2.INTER_AREA)
                if side_by_side:
                    shown = np.hstack([raw, pre.image])
                else:
                    shown = (raw if show_raw else pre.image).copy()

                h, w = pre.image.shape[:2]
                draw_overlay(
                    shown,
                    [
                        f"FPS {fps:5.1f}  preprocess {pre_ms:4.1f} ms",
                        f"brightness {pre.brightness:5.1f}  IR {pre.is_ir}",
                        f"frame {pre.frame_id}  dropped {source.dropped_frames}  {w}x{h}",
                        "view: " + ("raw | processed" if side_by_side else ("raw" if show_raw else "processed")),
                    ],
                )

            if shown is not None:
                cv2.imshow(WINDOW, shown)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r"):
                show_raw = not show_raw
            elif key == ord("s"):
                side_by_side = not side_by_side
            elif key == ord(" "):
                paused = not paused
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break

    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
