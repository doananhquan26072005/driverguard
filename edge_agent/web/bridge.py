"""In-browser agent: blocks 4-14 glue for Pyodide (frontend #/live).

The browser runs block 1 (getUserMedia), block 3 (MediaPipe Tasks JS, the same
face_landmarker.task) and the YOLO inference of block 4 (onnxruntime-web, the same
yolov8n.onnx). Per frame it hands this module plain numbers: the 478 landmarks, the
eyeBlink blendshapes, the face brightness. Everything from block 6 on is the same Python
as edge_agent.main, run by Pyodide in the page.

Differences from the device, forced by the browser:
- block 2: no CLAHE (MediaPipe gets the camera frame as is). The browser measures the raw
  numbers (channel difference, face luminance); the thresholds are applied here.
- block 5: eye_state.source = blendshape (MediaPipe eyeBlink, no eye-crop classifier).
- block 14: records are handed back to the browser as batch bodies; it posts them to
  /api/v1/web/events with the signed-in user's token.

Images never reach this module: only landmarks, blendshape scores and the YOLO output tensor.
Every entry point takes plain numbers, so it is tested without a browser.
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.config import PROJECT_ROOT, load_thresholds
from edge_agent.context.can_sim import CanSimulator, load_scenario
from edge_agent.context.vehicle_context import ContextConfig
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.hud.server import HudConfig, HudState
from edge_agent.io.publisher import (
    PublisherConfig,
    batch_body,
    build_event,
    build_feedback,
    build_sample,
    build_system_event,
)
from edge_agent.io.remote_config import apply_overrides
from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator
from edge_agent.perception.features import FeatureConfig, FeatureExtractor
from edge_agent.perception.landmarks import FaceLandmarks, LandmarkConfig, in_frame_ratio
from edge_agent.perception.phone_detector import (
    FaceBoxMemory,
    PhoneDetection,
    PhoneDetectorConfig,
    decode_yolov8,
    face_bbox,
    phone_near_face,
)
from edge_agent.perception.preprocess import PreprocessConfig, PreprocessedFrame

SCENARIOS = ("city_day", "highway_night", "parked")
NUM_LANDMARKS = 478
MAX_RECORDS_PER_BATCH = 100  # backend: MAX_EVENTS_PER_BATCH per list


def web_thresholds(overrides: dict[str, float] | None = None) -> tuple[dict[str, Any], list[str]]:
    """thresholds.yaml + tuned overrides from the backend, with the browser's block 5 source."""
    th = load_thresholds()
    problems: list[str] = []
    if overrides:
        th, problems = apply_overrides(th, overrides)
    th = copy.deepcopy(th)
    th["eye_state"] = {**(th.get("eye_state") or {}), "source": "blendshape"}
    return th, problems


def _floats(values: Any) -> np.ndarray:
    """A JS typed array (Pyodide proxy), a buffer or a list -> float32 numpy array."""
    if hasattr(values, "to_py"):
        values = values.to_py()
    if isinstance(values, memoryview):
        return np.frombuffer(values, dtype=np.float32).copy()
    return np.asarray(values, dtype=np.float32)


@dataclass(frozen=True)
class _PhoneResult:
    detections: tuple[PhoneDetection, ...]
    timestamp: float  # time of the frame YOLO looked at


class WebAgent:
    """One trip in the browser. All times are the browser's clock in seconds (performance.now() / 1000)."""

    def __init__(
        self,
        device_id: str,
        trip_id: str,
        scenario: str = "city_day",
        overrides: dict[str, float] | None = None,
    ) -> None:
        if scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}")
        th, self.problems = web_thresholds(overrides)
        self.device_id = device_id
        self.trip_id = trip_id
        self.extractor = FeatureExtractor(FeatureConfig.from_dict(th.get("features")))
        self.eye_state = EyeStateEstimator(EyeStateConfig.from_dict(th.get("eye_state")))
        self.phone_cfg = PhoneDetectorConfig.from_dict(th.get("phone"))
        self.preprocess_cfg = PreprocessConfig.from_dict(th.get("preprocess"))
        self.landmark_cfg = LandmarkConfig.from_dict(th.get("landmarks"))
        self.publisher_cfg = PublisherConfig.from_dict(th.get("publisher"))
        self.face_memory = FaceBoxMemory(self.phone_cfg.face_memory_s)
        self.can = CanSimulator(
            load_scenario(PROJECT_ROOT / "config" / "scenarios" / f"{scenario}.yaml"),
            moving_kmh=ContextConfig.from_dict(th.get("context")).min_speed_kmh,
        )
        self.decisions = DecisionPipeline(th)
        self.hud = HudState(HudConfig.from_dict(th.get("hud")))
        self._phone: _PhoneResult | None = None
        self._records: list[dict[str, Any]] = []
        self._t0: float | None = None
        self._bins_sent = 0
        self._minute_max_level = 0
        self._last_speed: float | None = None
        self._last_t: float | None = None
        self._fps = 0.0

    def settings(self) -> str:
        """What the browser side needs from thresholds.yaml (JSON): it keeps no thresholds of its own."""
        lm, ph, pub = self.landmark_cfg, self.phone_cfg, self.publisher_cfg
        return json.dumps(
            {
                "target_width": self.preprocess_cfg.target_width,
                "landmarks": {
                    "num_faces": lm.num_faces,
                    "min_face_detection_confidence": lm.min_face_detection_confidence,
                    "min_face_presence_confidence": lm.min_face_presence_confidence,
                    "min_tracking_confidence": lm.min_tracking_confidence,
                    "blendshapes": lm.blendshapes,
                },
                "phone": {"input_size": ph.input_size, "target_fps": ph.target_fps},
                "flush_interval_s": pub.flush_interval_s,
                "problems": self.problems,
            }
        )

    # ------------------------------------------------------------------ block 4 (YOLO output from the browser)
    def phone_output(
        self,
        output: Any,
        num_boxes: int,
        scale: float,
        pad_x: int,
        pad_y: int,
        width: int,
        height: int,
        t: float,
    ) -> int:
        """Raw YOLOv8 output (1, 4 + C, num_boxes) of the frame taken at t -> number of phones found."""
        raw = _floats(output).reshape(1, -1, num_boxes)
        cfg = self.phone_cfg
        dets = decode_yolov8(
            raw, cfg.class_id, cfg.conf_threshold, cfg.iou_threshold, scale, (pad_x, pad_y), (width, height)
        )
        self._phone = _PhoneResult(dets, t)
        return len(dets)

    def _phone_flag(self, face: tuple[float, float, float, float] | None, t: float) -> bool | None:
        result = self._phone
        if result is None or t - result.timestamp > self.phone_cfg.max_result_age_s:
            return None  # unknown, as on the device when YOLO is late
        return phone_near_face(result.detections, face, self.phone_cfg)

    # ------------------------------------------------------------------ blocks 3 (numbers) -> 6, 5, 7-12, 13, 14
    def frame(
        self,
        t: float,
        frame_id: int,
        width: int,
        height: int,
        points: Any | None,
        num_faces: int = 0,
        eye_blink: Sequence[float] | None = None,
        channel_diff: float = 255.0,
        brightness: float = 128.0,
    ) -> str:
        """One camera frame. points: 478 x (x, y, z) in pixels (z scaled like x), or None without a face.

        channel_diff: mean |B - G|, |G - R| of the frame (block 2's IR test, 0 = grayscale / infrared).
        brightness: mean luminance 0-255 of the face (landmark box), of the frame without a face.
        Returns the HUD state (JSON), the same document the device's HUD server serves at /state.
        """
        if self._t0 is None:
            self._t0 = t
        lm = None
        if points is not None:
            pts = _floats(points).reshape(NUM_LANDMARKS, 3)
            blink = None if eye_blink is None else (float(eye_blink[0]), float(eye_blink[1]))
            lm = FaceLandmarks(
                points=pts,
                image_width=width,
                image_height=height,
                face_conf=in_frame_ratio(pts, width, height),
                num_faces=max(num_faces, 1),
                frame_id=frame_id,
                timestamp=t,
                eye_blink=blink,
            )
        face = self.face_memory.update(face_bbox(lm.points) if lm is not None else None, t)
        phone_flag = self._phone_flag(face, t)
        features = self.extractor(lm, frame_id, t)  # 6
        pre = PreprocessedFrame(  # block 5 only reads the brightness / IR flag of block 2
            image=np.empty((0, 0, 3), np.uint8),
            gray=np.empty((0, 0), np.uint8),
            brightness=float(brightness),
            is_ir=float(channel_diff) <= self.preprocess_cfg.ir_channel_diff_max,
            scale=1.0,
            frame_id=frame_id,
            timestamp=t,
        )
        features = self.eye_state(pre, lm, features)  # 5
        signals = self.can.sample(t - self._t0)  # 10 (CAN)
        self._last_speed = signals.speed_kmh
        r = self.decisions.step(features, phone_flag, signals)  # 7, 8, 10, 11, 9, 12

        if self._last_t is not None and t > self._last_t:
            dt = t - self._last_t
            self._fps = 1.0 / dt if self._fps == 0 else 0.9 * self._fps + 0.1 / dt
        self._last_t = t
        self.hud.update(r, self._fps)  # 13
        self._minute_max_level = max(self._minute_max_level, r.alert.active_level)
        if r.alert.new_alert is not None:  # 13, 14
            event = build_event(r.alert.new_alert, r, self.trip_id)
            self.hud.add_alert(event["event_id"], r.alert.new_alert.level, r.alert.new_alert.reasons)
            self._records.append({"kind": "event", "data": event})
        if r.trip.bins_completed > self._bins_sent:  # a minute just closed: one fatigue timeline point
            self._bins_sent = r.trip.bins_completed
            if r.trip.minute_scores:
                sample = build_sample(
                    r.trip.minute_scores[-1], r.drowsiness.perclos_60s, self._minute_max_level, self.trip_id
                )
                self._records.append({"kind": "sample", "data": sample})
            self._minute_max_level = r.alert.active_level
        state = self.hud.to_json()
        state["measures"] = {  # for the camera overlay of #/live
            "face": features.face_found,
            "ear": None if features.ear is None else round(features.ear, 3),
            "mar": None if features.mar is None else round(features.mar, 3),
            "yaw": None if features.yaw is None else round(features.yaw, 1),
            "pitch": None if features.pitch is None else round(features.pitch, 1),
            "phone": phone_flag,
        }
        return json.dumps(state)

    # ------------------------------------------------------------------ HUD buttons, camera status
    def false_alarm(self, event_id: str) -> str:
        """The driver pressed "false alarm": 'ok', 'unknown', 'expired' or 'duplicate'."""
        result = self.hud.mark_false_alarm(event_id)
        if result == "ok":
            self._records.append({"kind": "feedback", "data": build_feedback(event_id)})
        return result

    def camera(self, lost: bool) -> None:
        """Camera track ended / came back: the dashboard learns this driver is (not) monitored."""
        self.hud.set_camera_lost(lost)
        reason = "camera_lost" if lost else "camera_restored"
        self._records.append({"kind": "event", "data": build_system_event(reason, self.trip_id, self._last_speed)})

    # ------------------------------------------------------------------ block 14 (the browser posts it)
    def take_batch(self) -> str | None:
        """Pending records as one POST body (JSON), or None. The browser re-sends it on failure."""
        if not self._records:
            return None
        records, self._records = self._records[:MAX_RECORDS_PER_BATCH], self._records[MAX_RECORDS_PER_BATCH:]
        return json.dumps(batch_body(self.device_id, records))
