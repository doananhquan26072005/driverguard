"""M87 - A face drawn with ellipses and lines, for running the real models where no camera or video is.

Not a picture of a person: skin-coloured ellipse, two eyes, brows, nose, mouth, hair, shoulders. MediaPipe's
face landmarker finds it on every frame (478 landmarks, EAR about 0.4 with the eyes drawn open, under 0.1
with them drawn shut), so CI can run blocks 3, 5 and 6 on the real model files and time the main loop with
the landmark model working (tools/benchmark.py --condition drawn_face). Frames are made in RAM.

It says nothing about accuracy on real faces, and YOLO sees no phone in it (nothing drawn looks like one).
"""

from __future__ import annotations

import cv2
import numpy as np

BACKGROUND = (90, 80, 70)  # BGR
SKIN = (140, 170, 215)
HAIR = (30, 30, 40)
SHIRT = (60, 60, 120)
EYE_WHITE = (240, 240, 240)
IRIS = (60, 50, 40)
PUPIL = (10, 10, 10)
LINE = (40, 40, 50)
NOSE = (100, 130, 180)
LIPS = (90, 90, 190)


def drawn_face(width: int = 1280, height: int = 720, eyes_open: bool = True, dx: int = 0) -> np.ndarray:
    """BGR image with the face in the middle, shifted dx pixels sideways."""
    img = np.full((height, width, 3), BACKGROUND, np.uint8)
    cx, cy = width // 2 + dx, height // 2
    cv2.rectangle(img, (cx - 150, cy + 150), (cx + 150, height), SHIRT, -1)
    cv2.rectangle(img, (cx - 35, cy + 100), (cx + 35, cy + 170), SKIN, -1)
    cv2.ellipse(img, (cx, cy - 20), (105, 140), 0, 180, 360, HAIR, -1)
    cv2.ellipse(img, (cx, cy), (95, 125), 0, 0, 360, SKIN, -1)
    for side in (-40, 40):
        ex, ey = cx + side, cy - 25
        cv2.ellipse(img, (ex, ey - 22), (24, 5), 0, 0, 360, LINE, -1)
        if eyes_open:
            cv2.ellipse(img, (ex, ey), (20, 10), 0, 0, 360, EYE_WHITE, -1)
            cv2.circle(img, (ex, ey), 9, IRIS, -1)
            cv2.circle(img, (ex, ey), 4, PUPIL, -1)
        else:
            cv2.line(img, (ex - 20, ey), (ex + 20, ey), LINE, 3)
    cv2.line(img, (cx, cy - 10), (cx - 8, cy + 28), NOSE, 3)
    cv2.line(img, (cx - 8, cy + 28), (cx + 10, cy + 28), NOSE, 3)
    cv2.ellipse(img, (cx, cy + 65), (32, 9), 0, 0, 360, LIPS, -1)
    return cv2.GaussianBlur(img, (5, 5), 0)


def drawn_face_frames(n: int, width: int = 1280, height: int = 720) -> tuple[list[np.ndarray], str]:
    """n frames, eyes open, the face moving a few pixels like a head that is never perfectly still."""
    sway = [drawn_face(width, height, dx=dx) for dx in (-2, -1, 0, 1, 2, 1, 0, -1)]
    frames = [sway[i % len(sway)] for i in range(n)]
    return frames, f"drawn face {width}x{height}, {n} frames (shapes, not a person: timings of a found face)"
