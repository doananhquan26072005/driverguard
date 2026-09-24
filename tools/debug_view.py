"""Debug viewer: blocks 1-8 (capture to drowsiness / distraction).

Shows the preprocessed stream with face landmarks, head pose axis, EAR / MAR /
pitch / yaw / roll, and prints EAR for every frame to the terminal.
Drowsiness events ([DROWSY] ...) are always printed, also with --quiet.
On-screen numbers are smoothed (--smooth) and refreshed 5x/s; the graphs below the
video show the raw per-frame values of the last few seconds.
Display only - frames are never written to disk.

    python tools/debug_view.py --source 0                # webcam
    python tools/debug_view.py --source path/to/video.mp4 --loop
    python tools/debug_view.py --source 0 --quiet        # no per-frame terminal output
    python tools/debug_view.py --source 0 --speed 50     # simulated vehicle speed (km/h)

Keys: q / ESC quit, r raw vs processed, s side-by-side, l landmarks, g graphs,
      m toggle moving / stopped (speed gating), space pause.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from edge_agent.analysis.distraction import DistractionAnalyzer, DistractionConfig, DistractionState  # noqa: E402
from edge_agent.analysis.drowsiness import (  # noqa: E402
    DrowsinessAnalyzer,
    DrowsinessConfig,
    DrowsinessState,
    describe_events,
)
from edge_agent.capture import CaptureConfig, FrameSource  # noqa: E402
from edge_agent.config import load_thresholds  # noqa: E402
from edge_agent.perception import PreprocessConfig, Preprocessor  # noqa: E402
from edge_agent.perception.eye_state import EyeStateConfig, make_estimator  # noqa: E402
from edge_agent.perception.features import (  # noqa: E402
    LEFT_EYE,
    MOUTH_CORNERS,
    MOUTH_VERTICAL_PAIRS,
    POSE_LANDMARKS,
    RIGHT_EYE,
    FeatureConfig,
    FeatureExtractor,
    FrameFeatures,
    camera_matrix,
)
from edge_agent.perception.landmarks import FaceLandmarkDetector, FaceLandmarks, LandmarkConfig  # noqa: E402
from edge_agent.perception.phone_detector import (  # noqa: E402
    AsyncPhoneDetector,
    BBox,
    FaceBoxMemory,
    PhoneDetectorConfig,
    PhoneResult,
    driver_zone,
    face_bbox,
    phone_near_face,
)

WINDOW = "DriverGuard debug"
MOUTH_POINTS = MOUTH_CORNERS + tuple(i for pair in MOUTH_VERTICAL_PAIRS for i in pair)


def to_bgr(image: np.ndarray) -> np.ndarray:
    if image.ndim == 2 or image.shape[2] == 1:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    return image


GREEN, RED, ORANGE, GRAY = (0, 255, 0), (0, 0, 255), (0, 165, 255), (150, 150, 150)
Line = str | tuple[str, tuple[int, int, int]]  # text, or (text, BGR color)


def draw_overlay(image: np.ndarray, lines: list[Line]) -> None:
    # Dark box behind single-stroke text: in OpenCV 5 glyph width depends on thickness,
    # so the usual thick-outline + thin-text trick no longer lines up.
    font, scale, line_h = cv2.FONT_HERSHEY_SIMPLEX, 0.5, 20
    items = [(ln, GREEN) if isinstance(ln, str) else ln for ln in lines]
    width = max(cv2.getTextSize(t, font, scale, 1)[0][0] for t, _ in items)
    box = image[4 : 10 + line_h * len(items), 4 : 16 + width]
    box[:] = (box * 0.35).astype(np.uint8)
    for i, (text, color) in enumerate(items):
        cv2.putText(image, text, (10, 20 + i * line_h), font, scale, color, 1, cv2.LINE_AA)


def draw_phone(image: np.ndarray, result: PhoneResult | None, face: BBox | None, cfg: PhoneDetectorConfig) -> None:
    """Driver zone (thin) and phone boxes: orange inside the zone, gray outside."""
    if face is not None:
        zx1, zy1, zx2, zy2 = (int(v) for v in driver_zone(face, cfg))
        cv2.rectangle(image, (zx1, zy1), (zx2, zy2), (90, 90, 90), 1)
    if result is None:
        return
    for det in result.detections:
        inside = phone_near_face((det,), face, cfg)
        x1, y1, x2, y2 = (int(v) for v in det.bbox)
        color = ORANGE if inside else GRAY
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        cv2.putText(image, f"phone {det.score:.2f}", (x1, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)


def distraction_lines(
    d: DistractionState, phone_flag: bool | None, phone: PhoneResult | None, speed: float | None
) -> list[Line]:
    speed_txt = "unknown" if speed is None else f"{speed:.0f} km/h"
    if not d.active:
        return [(f"DISTRACTION OFF (stopped, speed {speed_txt})", GRAY)]
    yolo = "YOLO off" if phone is None else f"YOLO {phone.inference_ms:4.0f} ms"
    flag = "--" if phone_flag is None else str(phone_flag)
    return [
        (f"off_road {d.off_road_duration:4.1f} s" + ("  OFF ROAD" if d.off_road else ""), RED if d.off_road else GREEN),
        (f"phone_ratio_2s {d.phone_ratio_2s:.2f}  phone_near_face {flag}", ORANGE if phone_flag else GREEN),
        f"speed {speed_txt}  baseline yaw {d.baseline_yaw:+.0f} pitch {d.baseline_pitch:+.0f}  {yolo}",
    ]


def drowsiness_lines(d: DrowsinessState, min_coverage_s: float, f: FrameFeatures) -> list[Line]:
    eyes = "--" if d.eye_closed is None else ("CLOSED" if d.eye_closed else "open")
    if d.eye_source == "cnn":  # block 5 decided: show its probability and why it was called
        eyes += f" [CNN p_closed {f.p_closed:.2f}, {f.eye_cnn_reason}]"
    elif d.eye_source == "ear":
        eyes += " [EAR]"
    warming = "" if d.perclos_coverage_s >= min_coverage_s else f" (warming up {d.perclos_coverage_s:.0f}s)"
    return [
        (
            f"eyes {eyes} {d.closed_duration:3.1f}s  PERCLOS {d.perclos_60s:.2f}{warming}  blinks {d.blink_rate:.0f}/min",
            RED if d.microsleep else GREEN,
        ),
        (
            f"yawns {d.yawn_count_10min}/10min  nods {d.nod_count_5min}/5min  "
            f"EAR open {d.ear_open_baseline:.3f} closed<{d.ear_closed_threshold:.3f}",
            ORANGE if d.yawning else GREEN,
        ),
    ]


def draw_landmarks(image: np.ndarray, lm: FaceLandmarks, extractor: FeatureExtractor) -> None:
    pts = lm.points[:, :2].astype(np.int32)
    for x, y in pts:
        cv2.circle(image, (int(x), int(y)), 1, (160, 160, 160), -1)
    for idx, color in ((RIGHT_EYE, (0, 255, 255)), (LEFT_EYE, (0, 255, 255)), (MOUTH_POINTS, (255, 0, 255))):
        for i in idx:
            cv2.circle(image, tuple(int(v) for v in pts[i]), 2, color, -1)
    for i in POSE_LANDMARKS:
        cv2.circle(image, tuple(int(v) for v in pts[i]), 3, (0, 0, 255), -1)

    # Head pose axes from the last solvePnP result: x red, y green, z (facing direction) blue.
    pose = extractor.pose_vectors
    if pose is None:
        return
    rvec, tvec = pose
    cam = camera_matrix(lm.image_width, lm.image_height, extractor.config.focal_length_scale)
    axes = np.float64([[0, 0, 0], [5, 0, 0], [0, 5, 0], [0, 0, -5]])  # model units ~cm
    proj, _ = cv2.projectPoints(axes, rvec, tvec, cam, np.zeros(4))
    o, *ends = [tuple(int(v) for v in p.ravel()) for p in proj]
    for end, color in zip(ends, ((0, 0, 255), (0, 255, 0), (255, 0, 0)), strict=True):
        cv2.line(image, o, end, color, 2, cv2.LINE_AA)


def fmt(value: float | None, spec: str = "6.3f") -> str:
    return "  --  " if value is None else format(value, spec)


SIGNALS = ("ear", "ear_left", "ear_right", "mar", "pitch", "yaw", "roll")


class DisplaySmoother:
    """Exponential moving average for on-screen numbers only (FrameFeatures stays raw)."""

    def __init__(self, tau: float) -> None:
        self.tau = tau
        self.values: dict[str, float] = {}
        self._last_t: float | None = None

    def update(self, f: FrameFeatures) -> dict[str, float]:
        if not f.face_found or self.tau <= 0:
            self.values, self._last_t = {}, None
            if f.face_found:
                self.values = {k: getattr(f, k) for k in SIGNALS if getattr(f, k) is not None}
            return self.values
        dt = 0.0 if self._last_t is None else f.timestamp - self._last_t
        self._last_t = f.timestamp
        alpha = 1.0 - np.exp(-dt / self.tau)
        for k in SIGNALS:
            v = getattr(f, k)
            if v is None:
                continue
            prev = self.values.get(k)
            self.values[k] = v if prev is None else prev + alpha * (v - prev)
        return self.values


# (label, field, color BGR, y min, y max) per plot panel; dashed guide lines at `guides`.
PLOTS = (
    ("EAR", (("ear", (0, 255, 255)),), 0.0, 0.5, (0.2,)),
    ("MAR", (("mar", (255, 0, 255)),), 0.0, 1.0, (0.5,)),
    ("pitch/yaw/roll", (("pitch", (0, 0, 255)), ("yaw", (0, 255, 0)), ("roll", (255, 128, 0))), -45.0, 45.0, (0.0,)),
)


def draw_plots(
    width: int,
    history: deque[FrameFeatures],
    window_s: float,
    guides_override: dict[str, tuple[float, ...]] | None = None,
    panel_h: int = 80,
) -> np.ndarray:
    """Scrolling graphs of the last `window_s` seconds of raw features, stacked vertically.

    `guides_override` replaces a panel's guide lines by label, e.g. the live EAR threshold.
    """
    panels = []
    now = history[-1].timestamp if history else 0.0
    for label, series, lo, hi, default_guides in PLOTS:
        guides = (guides_override or {}).get(label, default_guides)
        panel = np.full((panel_h, width, 3), 25, dtype=np.uint8)

        def to_y(v: float, lo: float = lo, hi: float = hi) -> int:
            return int(round((1.0 - (min(max(v, lo), hi) - lo) / (hi - lo)) * (panel_h - 1)))

        for g in guides:
            y = to_y(g)
            for x in range(0, width, 8):
                cv2.line(panel, (x, y), (x + 3, y), (90, 90, 90), 1)
        for field, color in series:
            segment: list[tuple[int, int]] = []
            for f in history:
                v = getattr(f, field)
                if v is None:  # no face: break the line
                    if len(segment) > 1:
                        cv2.polylines(panel, [np.array(segment, np.int32)], False, color, 1, cv2.LINE_AA)
                    segment = []
                    continue
                x = int((1.0 - (now - f.timestamp) / window_s) * (width - 1))
                segment.append((x, to_y(v)))
            if len(segment) > 1:
                cv2.polylines(panel, [np.array(segment, np.int32)], False, color, 1, cv2.LINE_AA)
        names = "  ".join(field for field, _ in series) if len(series) > 1 else label
        cv2.putText(
            panel, f"{names}  range {lo:g} to {hi:g}", (6, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1
        )
        panel[0, :] = 70
        panels.append(panel)
    return np.vstack(panels)


def feature_lines(values: dict[str, float], f: FrameFeatures, num_faces: int) -> list[str]:
    if not f.face_found:
        return ["NO FACE"]
    v = values.get
    return [
        f"EAR {fmt(v('ear'), '.3f')}  (L {fmt(v('ear_left'), '.3f')}  R {fmt(v('ear_right'), '.3f')})",
        f"MAR {fmt(v('mar'), '.3f')}  face_conf {f.face_conf:.2f}  faces {num_faces}",
        f"pitch {fmt(v('pitch'), '+.0f')}  yaw {fmt(v('yaw'), '+.0f')}  roll {fmt(v('roll'), '+.0f')}  deg",
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", default="0", help="camera index (e.g. 0) or video file path")
    parser.add_argument("--loop", action="store_true", help="loop the video file")
    parser.add_argument("--config", default=None, help="path to thresholds.yaml")
    parser.add_argument("--quiet", action="store_true", help="do not print EAR every frame")
    parser.add_argument("--smooth", type=float, default=0.3, help="display smoothing time constant in s (0 = raw)")
    parser.add_argument("--plot-seconds", type=float, default=5.0, help="time span of the graphs")
    parser.add_argument("--speed", type=float, default=None, help="simulated speed in km/h (default: unknown)")
    parser.add_argument("--no-phone", action="store_true", help="disable the YOLO phone detector")
    args = parser.parse_args()

    thresholds = load_thresholds(args.config)
    preprocessor = Preprocessor(PreprocessConfig.from_dict(thresholds.get("preprocess")))
    detector = FaceLandmarkDetector(LandmarkConfig.from_dict(thresholds.get("landmarks")))
    extractor = FeatureExtractor(FeatureConfig.from_dict(thresholds.get("features")))
    eye_state = make_estimator(EyeStateConfig.from_dict(thresholds.get("eye_state")))
    source = FrameSource(args.source, CaptureConfig.from_dict(thresholds.get("capture")), loop=args.loop)
    phone_cfg = PhoneDetectorConfig.from_dict(thresholds.get("phone"))
    phone_detector = None
    if not args.no_phone:
        try:
            phone_detector = AsyncPhoneDetector(phone_cfg)
        except FileNotFoundError as e:
            print(f"[phone] disabled: {e}")
    drowsiness = DrowsinessAnalyzer(DrowsinessConfig.from_dict(thresholds.get("drowsiness")))
    yawn_mar = drowsiness.config.yawn_mar_open
    distraction = DistractionAnalyzer(DistractionConfig.from_dict(thresholds.get("distraction")))
    moving_speed = args.speed if args.speed else 50.0
    speed: float | None = args.speed

    show_raw = False
    side_by_side = False
    show_landmarks = True
    show_plots = True
    paused = False
    fps = 0.0
    last_t = time.monotonic()
    shown = None
    smoother = DisplaySmoother(args.smooth)
    face_memory = FaceBoxMemory(phone_cfg.face_memory_s)
    history: deque[FrameFeatures] = deque()
    text_lines: list[Line] = []
    last_text_t = 0.0

    cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    if phone_detector is not None:
        phone_detector.start()
    with source, detector:
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
                t1 = time.perf_counter()
                lm = detector.detect(pre)
                t2 = time.perf_counter()
                feats = extractor(lm, pre.frame_id, pre.timestamp)
                if eye_state is not None:  # block 5, only when EAR is not reliable
                    feats = eye_state(pre, lm, feats)
                phone = None
                if phone_detector is not None:
                    phone_detector.submit(pre)  # YOLO runs on its own thread at ~5 FPS
                    phone = phone_detector.latest()
                face = face_memory.update(face_bbox(lm.points) if lm is not None else None, pre.timestamp)
                phone_flag = None if phone is None else phone_near_face(phone.detections, face, phone_cfg)
                dstate = distraction.update(feats, phone_flag, speed)
                drowsy = drowsiness.update(feats)
                t3 = time.perf_counter()

                now = time.monotonic()
                dt = now - last_t
                last_t = now
                if dt > 0:
                    fps = 1.0 / dt if fps == 0 else 0.9 * fps + 0.1 / dt

                for line in describe_events(drowsy):
                    print(f"frame {feats.frame_id:6d}  {line}")
                if not args.quiet:
                    if feats.face_found:
                        print(
                            f"frame {feats.frame_id:6d}  EAR {fmt(feats.ear)}  MAR {fmt(feats.mar)}  "
                            f"pitch {fmt(feats.pitch, '6.1f')}  yaw {fmt(feats.yaw, '6.1f')}  "
                            f"roll {fmt(feats.roll, '6.1f')}"
                        )
                    else:
                        print(f"frame {feats.frame_id:6d}  no face")

                raw = to_bgr(frame.image)
                if pre.scale != 1.0:
                    raw = cv2.resize(raw, (pre.image.shape[1], pre.image.shape[0]), interpolation=cv2.INTER_AREA)
                processed = pre.image.copy()
                target = processed if (side_by_side or not show_raw) else raw.copy()
                if show_landmarks and lm is not None:
                    draw_landmarks(target, lm, extractor)
                draw_phone(target, phone, face, phone_cfg)
                if side_by_side:
                    shown = np.hstack([raw, target])
                else:
                    shown = target

                values = smoother.update(feats)
                history.append(feats)
                while history and feats.timestamp - history[0].timestamp > args.plot_seconds:
                    history.popleft()

                # Refresh the text 5x per second so the digits are readable.
                if now - last_text_t >= 0.2 or not feats.face_found:
                    last_text_t = now
                    h, w = pre.image.shape[:2]
                    text_lines = [
                        f"FPS {fps:5.1f}  pre {(t1 - t0) * 1e3:4.1f} ms  mesh {(t2 - t1) * 1e3:4.1f} ms"
                        f"  feat {(t3 - t2) * 1e3:4.1f} ms",
                        f"brightness {pre.brightness:5.1f}  IR {pre.is_ir}  {w}x{h}",
                        f"frame {pre.frame_id}  dropped {source.dropped_frames}",
                        *feature_lines(values, feats, lm.num_faces if lm else 0),
                        *drowsiness_lines(drowsy, drowsiness.config.perclos_min_coverage_s, feats),
                        *distraction_lines(dstate, phone_flag, phone, speed),
                    ]
                draw_overlay(shown, text_lines)
                if show_plots:
                    shown = np.vstack(
                        [
                            shown,
                            draw_plots(
                                shown.shape[1],
                                history,
                                args.plot_seconds,
                                {"EAR": (drowsy.ear_closed_threshold,), "MAR": (yawn_mar,)},
                            ),
                        ]
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
            elif key == ord("l"):
                show_landmarks = not show_landmarks
            elif key == ord("g"):
                show_plots = not show_plots
            elif key == ord("m"):
                speed = 0.0 if (speed is None or speed > 0) else moving_speed
                print(f"[speed] {speed} km/h")
            elif key == ord(" "):
                paused = not paused
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break

    if phone_detector is not None:
        phone_detector.stop()
    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
