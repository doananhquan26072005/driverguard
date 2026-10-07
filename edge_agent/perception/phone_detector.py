"""Block 4 - Phone detector (YOLOv8n ONNX, COCO class "cell phone").

YOLO is too slow to run on every frame alongside MediaPipe, so it runs on its own
thread at ~`target_fps`. The main loop calls `submit()` every frame (only the newest
frame is kept) and reads `latest()`, which returns the most recent result. Results
older than `max_result_age_s` are treated as unknown.

A result is already `now - frame timestamp` old when inference finishes. On a CPU where
YOLO takes longer than `max_result_age_s`, every result would be unknown and phone detection
silently off: such results are counted (`stale_results`) and a warning is printed once.

`phone_near_face()` decides whether a detected phone is in the driver's zone
(around the face and down to the chest), so a passenger's phone does not count.
A phone held in front of the face often hides it from MediaPipe, so `FaceBoxMemory`
keeps the last face box for `face_memory_s` and the zone is still known.

`PhoneHealth` watches the share of frames left without a fresh result: when most of the last seconds
were "unknown", the driver and the backend are told that phone detection is not working (M50).

`phone_kind()` says how the phone in the driver zone is held, from where its box sits against the
face box: beside the face ("call"), below the chin ("text"), or neither ("unknown"). Recorded only
(metadata, trip summary): the alert reason and level stay `phone`, L2.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from edge_agent.config import PROJECT_ROOT, config_from_dict
from edge_agent.cv import cv2
from edge_agent.perception.geometry import nms
from edge_agent.perception.preprocess import PreprocessedFrame

BBox = tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels of the preprocessed image


@dataclass(frozen=True)
class PhoneDetectorConfig:
    model_path: str = "models/yolov8n.onnx"
    input_size: int = 640
    class_id: int = 67
    conf_threshold: float = 0.35
    iou_threshold: float = 0.45
    target_fps: float = 5.0
    num_threads: int = 2
    max_result_age_s: float = 0.6
    zone_expand_x: float = 1.0
    zone_expand_up: float = 0.5
    zone_expand_down: float = 1.5
    face_memory_s: float = 3.0
    # phone_kind(): phone centre against the face box, in face widths sideways from the face
    # centre and in face heights below the top of the face (0 = forehead, 1 = chin).
    kind_call_side_min: float = 0.35
    kind_call_below_max: float = 1.0
    kind_text_below_min: float = 1.0
    # PhoneHealth (M50): share of the last unknown_window_s without a fresh result.
    unknown_window_s: float = 10.0
    unknown_ratio: float = 0.8
    unknown_clear_ratio: float = 0.5

    @classmethod
    def from_dict(cls, d: dict[str, Any] | None) -> PhoneDetectorConfig:
        return config_from_dict(cls, d, "phone")

    def resolved_model_path(self) -> Path:
        p = Path(self.model_path)
        return p if p.is_absolute() else PROJECT_ROOT / p


@dataclass(frozen=True)
class PhoneDetection:
    bbox: BBox
    score: float


@dataclass(frozen=True)
class PhoneResult:
    detections: tuple[PhoneDetection, ...]
    frame_id: int  # frame the detection ran on
    timestamp: float  # timestamp of that frame
    inference_ms: float = 0.0
    finished_at: float = field(default=0.0)  # time.monotonic() when inference finished


# --------------------------------------------------------------------------- geometry


def face_bbox(points: np.ndarray) -> BBox:
    x1, y1 = points[:, :2].min(axis=0)
    x2, y2 = points[:, :2].max(axis=0)
    return float(x1), float(y1), float(x2), float(y2)


def driver_zone(face: BBox, cfg: PhoneDetectorConfig) -> BBox:
    """Face box grown sideways (ear / call), a bit up, and down to the chest (texting)."""
    x1, y1, x2, y2 = face
    w, h = x2 - x1, y2 - y1
    return (
        x1 - cfg.zone_expand_x * w,
        y1 - cfg.zone_expand_up * h,
        x2 + cfg.zone_expand_x * w,
        y2 + cfg.zone_expand_down * h,
    )


def phone_near_face(detections: tuple[PhoneDetection, ...], face: BBox | None, cfg: PhoneDetectorConfig) -> bool:
    """True if the centre of any detected phone lies inside the driver zone."""
    if face is None:
        return False
    zx1, zy1, zx2, zy2 = driver_zone(face, cfg)
    for det in detections:
        cx = (det.bbox[0] + det.bbox[2]) / 2.0
        cy = (det.bbox[1] + det.bbox[3]) / 2.0
        if zx1 <= cx <= zx2 and zy1 <= cy <= zy2:
            return True
    return False


PHONE_KINDS = ("call", "text", "unknown")


def phone_kind(detections: tuple[PhoneDetection, ...], face: BBox | None, cfg: PhoneDetectorConfig) -> str | None:
    """How the best-scored phone inside the driver zone is held: "call" (beside the face, at or above
    the chin), "text" (below the chin), "unknown" (e.g. in front of the face). None: no phone there."""
    if face is None:
        return None
    zx1, zy1, zx2, zy2 = driver_zone(face, cfg)
    x1, y1, x2, y2 = face
    w, h = x2 - x1, y2 - y1
    if w <= 0 or h <= 0:
        return None
    for det in detections:  # sorted by score, best first
        cx = (det.bbox[0] + det.bbox[2]) / 2.0
        cy = (det.bbox[1] + det.bbox[3]) / 2.0
        if not (zx1 <= cx <= zx2 and zy1 <= cy <= zy2):
            continue
        side = abs(cx - (x1 + x2) / 2.0) / w
        below = (cy - y1) / h
        if side >= cfg.kind_call_side_min and below <= cfg.kind_call_below_max:
            return "call"
        if below >= cfg.kind_text_below_min:
            return "text"
        return "unknown"
    return None


class FaceBoxMemory:
    """Last seen face box, reused for up to `max_age_s` after the face is lost.

    Call `update()` every frame with the current face box (None when no face).
    """

    def __init__(self, max_age_s: float) -> None:
        self.max_age_s = max_age_s
        self._face: BBox | None = None
        self._seen_at: float | None = None

    def update(self, face: BBox | None, t: float) -> BBox | None:
        if face is not None:
            self._face, self._seen_at = face, t
            return face
        if self._seen_at is not None and t - self._seen_at <= self.max_age_s:
            return self._face
        return None


class PhoneHealth:
    """Is the phone detector still telling the loop anything? (M50)

    Every frame without a fresh result (YOLO slower than `max_result_age_s`, not loaded, crashed) is
    "unknown" to block 8, which then simply never sees a phone: silent. Once at least
    `unknown_ratio` of the last `unknown_window_s` was unknown, phone detection is unavailable; it is
    back when the share falls to `unknown_clear_ratio`. Nothing is judged before one full window of
    frames (the first result needs a moment). Pure logic on the frame times it is given.
    """

    def __init__(self, config: PhoneDetectorConfig) -> None:
        self.config = config
        self.unavailable = False
        self._window: deque[tuple[float, float, bool]] = deque()  # (t, dt, unknown)
        self._total = 0.0
        self._unknown = 0.0
        self._unknown_n = 0
        self._last_t: float | None = None

    @property
    def unknown_share(self) -> float:
        return min(max(self._unknown / self._total, 0.0), 1.0) if self._total > 1e-9 else 0.0

    def update(self, t: float, known: bool) -> bool:
        """One frame at time t; known: block 4 gave a fresh answer for it. Returns `unavailable`."""
        cfg = self.config
        if cfg.unknown_window_s <= 0:
            return False
        dt = 0.0 if self._last_t is None else min(max(t - self._last_t, 0.0), cfg.max_result_age_s)
        self._last_t = t
        self._window.append((t, dt, not known))
        self._total += dt
        if not known:
            self._unknown += dt
            self._unknown_n += 1
        while self._window and t - self._window[0][0] > cfg.unknown_window_s:
            _, old_dt, unknown = self._window.popleft()
            self._total -= old_dt
            if unknown:
                self._unknown -= old_dt
                self._unknown_n -= 1
        if self._unknown_n == 0:
            self._unknown = 0.0
        full = t - self._window[0][0] >= cfg.unknown_window_s - cfg.max_result_age_s
        if not full:
            return self.unavailable
        share = self.unknown_share
        if not self.unavailable and share >= cfg.unknown_ratio:
            self.unavailable = True
        elif self.unavailable and share <= cfg.unknown_clear_ratio:
            self.unavailable = False
        return self.unavailable


# --------------------------------------------------------------------------- YOLO model


def letterbox(image: np.ndarray, size: int) -> tuple[np.ndarray, float, tuple[int, int]]:
    """Resize keeping aspect ratio and pad to size x size. Returns (image, scale, (pad_x, pad_y))."""
    h, w = image.shape[:2]
    scale = min(size / w, size / h)
    nw, nh = round(w * scale), round(h * scale)
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)
    pad_x, pad_y = (size - nw) // 2, (size - nh) // 2
    out = np.full((size, size, 3), 114, dtype=np.uint8)
    out[pad_y : pad_y + nh, pad_x : pad_x + nw] = resized
    return out, scale, (pad_x, pad_y)


def decode_yolov8(
    output: np.ndarray,
    class_id: int,
    conf_threshold: float,
    iou_threshold: float,
    scale: float,
    pad: tuple[int, int],
    image_size: tuple[int, int],
) -> tuple[PhoneDetection, ...]:
    """YOLOv8 raw output (1, 4 + num_classes, N) -> phone detections in original image pixels."""
    preds = output[0].T  # (N, 4 + C): cx, cy, w, h, class scores
    scores = preds[:, 4 + class_id]
    keep = scores >= conf_threshold
    if not np.any(keep):
        return ()
    boxes, scores = preds[keep, :4], scores[keep]
    x1 = (boxes[:, 0] - boxes[:, 2] / 2 - pad[0]) / scale
    y1 = (boxes[:, 1] - boxes[:, 3] / 2 - pad[1]) / scale
    bw, bh = boxes[:, 2] / scale, boxes[:, 3] / scale
    xywh = np.stack([x1, y1, bw, bh], axis=1)
    if cv2 is None:  # browser build (geometry.py)
        idx = nms(xywh, scores, conf_threshold, iou_threshold)
    else:
        idx = cv2.dnn.NMSBoxes(xywh.tolist(), scores.tolist(), conf_threshold, iou_threshold)
    w, h = image_size
    dets = []
    for i in np.array(idx).reshape(-1):
        bx1, by1 = max(0.0, float(x1[i])), max(0.0, float(y1[i]))
        bx2, by2 = min(float(w), float(x1[i] + bw[i])), min(float(h), float(y1[i] + bh[i]))
        dets.append(PhoneDetection(bbox=(bx1, by1, bx2, by2), score=float(scores[i])))
    return tuple(sorted(dets, key=lambda d: -d.score))


class YoloPhoneModel:
    """Synchronous YOLOv8n ONNX inference returning phone detections only."""

    def __init__(self, config: PhoneDetectorConfig | None = None) -> None:
        from edge_agent.perception.onnx import load_ort  # imported here so the rest of the package works without it

        ort = load_ort()

        self.config = config or PhoneDetectorConfig()
        model = self.config.resolved_model_path()
        if not model.exists():
            raise FileNotFoundError(f"Model not found: {model}. See tools/download_models.py")
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = self.config.num_threads  # leave CPU for the main loop
        opts.inter_op_num_threads = 1
        # YOLO runs ~5x/s: idle pool threads must sleep, not busy-wait on cores MediaPipe needs
        # (measured: -22% CPU of this thread, same latency).
        opts.add_session_config_entry("session.intra_op.allow_spinning", "0")
        self._session = ort.InferenceSession(str(model), opts, providers=["CPUExecutionProvider"])
        self._input_name = self._session.get_inputs()[0].name

    def __call__(self, image: np.ndarray) -> tuple[PhoneDetection, ...]:
        cfg = self.config
        boxed, scale, pad = letterbox(image, cfg.input_size)
        blob = cv2.dnn.blobFromImage(boxed, 1.0 / 255.0, swapRB=True)  # BGR -> RGB, NCHW float32
        output = self._session.run(None, {self._input_name: blob})[0]
        h, w = image.shape[:2]
        return decode_yolov8(output, cfg.class_id, cfg.conf_threshold, cfg.iou_threshold, scale, pad, (w, h))


# --------------------------------------------------------------------------- async wrapper


class AsyncPhoneDetector:
    """Runs a phone model on a background thread at most `target_fps` times per second."""

    def __init__(
        self,
        config: PhoneDetectorConfig | None = None,
        model: Callable[[np.ndarray], tuple[PhoneDetection, ...]] | None = None,
    ) -> None:
        self.config = config or PhoneDetectorConfig()
        self._model = model if model is not None else YoloPhoneModel(self.config)
        self._cond = threading.Condition()
        self._pending: PreprocessedFrame | None = None
        self._result: PhoneResult | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.runs = 0
        self.stale_results = 0  # results already older than max_result_age_s when they arrived

    def start(self) -> AsyncPhoneDetector:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="PhoneDetector", daemon=True)
            self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        with self._cond:
            self._cond.notify_all()
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None
        self._pending = None

    def __enter__(self) -> AsyncPhoneDetector:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def submit(self, frame: PreprocessedFrame) -> None:
        """Offer the newest frame. Cheap: only replaces a reference."""
        with self._cond:
            self._pending = frame
            self._cond.notify()

    def latest(self, now: float | None = None) -> PhoneResult | None:
        """Most recent result, or None if there is none or it is older than max_result_age_s."""
        result = self._result
        if result is None:
            return None
        now = time.monotonic() if now is None else now
        if now - result.timestamp > self.config.max_result_age_s:
            return None
        return result

    def _run(self) -> None:
        period = 1.0 / self.config.target_fps if self.config.target_fps > 0 else 0.0
        next_run = time.monotonic()
        while not self._stop.is_set():
            delay = next_run - time.monotonic()
            if delay > 0 and self._stop.wait(delay):
                break
            with self._cond:
                while self._pending is None and not self._stop.is_set():
                    self._cond.wait(0.5)
                frame, self._pending = self._pending, None
            if frame is None:
                break
            t0 = time.perf_counter()
            detections = self._model(frame.image)
            infer_ms = (time.perf_counter() - t0) * 1000.0
            self._result = PhoneResult(
                detections=detections,
                frame_id=frame.frame_id,
                timestamp=frame.timestamp,
                inference_ms=infer_ms,
                finished_at=time.monotonic(),
            )
            self.runs += 1
            age_s = self._result.finished_at - frame.timestamp
            if age_s > self.config.max_result_age_s:
                self.stale_results += 1
                if self.stale_results == 1:
                    print(
                        f"[phone] WARNING: result arrived {age_s * 1000:.0f} ms after its frame "
                        f"(inference {infer_ms:.0f} ms) > phone.max_result_age_s "
                        f"({self.config.max_result_age_s * 1000:.0f} ms): it counts as unknown. If this "
                        "keeps happening, phone detection is effectively off: use a smaller / INT8 model"
                    )
            next_run = max(next_run + period, time.monotonic())
