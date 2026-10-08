"""In-browser agent: blocks 4-14 glue for Pyodide (frontend #/live).

The browser runs block 1 (getUserMedia), block 3 (MediaPipe Tasks JS, the same
face_landmarker.task) and the YOLO inference of block 4 (onnxruntime-web, the same
yolov8n.onnx). Per frame it hands this module plain numbers: the 478 landmarks, the
eyeBlink blendshapes, the face brightness. Everything from block 6 on is the same Python
as edge_agent.main, run by Pyodide in the page. The browser hands over every face it sees;
which one is the driver is decided here (block 3's DriverSelector: the largest face until
driver enrollment, then the enrolled one), as on the device.

Differences from the device, forced by the browser:
- block 2: no CLAHE (MediaPipe gets the camera frame as is). The browser measures the raw
  numbers (channel difference, face luminance); the thresholds are applied here.
- block 5: eye_state.source = blendshape (MediaPipe eyeBlink, no eye-crop classifier).
- block 14: records are handed back to the browser as batch bodies; it posts them to
  /api/v1/web/events with the signed-in user's token.
- block 1: the page watches its own camera loop with block 1's numbers (`capture` in `settings`): a
  camera that stops giving frames is `camera(True)` and is asked for again (`camera_attempts`), and
  a frame that fails in the page's own code is reported with `frame_error` (M71).

What happens after the features (blocks 6-12, HUD state, block 14 records, end of trip) is
edge_agent.runtime.TripRuntime, shared with the device. Images never reach this module: only
landmarks, blendshape scores and the YOLO output tensor.
Every entry point takes plain numbers, so it is tested without a browser.
"""

from __future__ import annotations

import copy
import dataclasses
import json
import traceback
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from edge_agent.capture.frame_source import CaptureConfig
from edge_agent.config import PROJECT_ROOT, load_thresholds
from edge_agent.context.can_sim import SIM, CanSimulator, ExternalVehicle, load_scenario
from edge_agent.context.vehicle_context import ContextConfig
from edge_agent.io.publisher import PublisherConfig, batch_body, is_urgent, perf_record
from edge_agent.io.remote_config import ThresholdReloader, apply_overrides
from edge_agent.perception.eye_state import EyeStateConfig, EyeStateEstimator
from edge_agent.perception.features import FeatureConfig, FeatureExtractor
from edge_agent.perception.landmarks import DriverSelector, FaceLandmarks, LandmarkConfig, in_frame_ratio
from edge_agent.perception.phone_detector import (
    FaceBoxMemory,
    PhoneDetection,
    PhoneDetectorConfig,
    decode_yolov8,
    face_bbox,
    phone_kind,
    phone_near_face,
)
from edge_agent.perception.preprocess import PreprocessConfig, PreprocessedFrame
from edge_agent.runtime import TripRuntime
from edge_agent.version import bundled_models, version_info

SCENARIOS = (SIM, "city_day", "highway_night", "parked")  # sim: speed from tools/drive_sim.py via the page
NUM_LANDMARKS = 478
MAX_RECORDS_PER_BATCH = 100  # backend: MAX_EVENTS_PER_BATCH per list


def web_thresholds(
    overrides: dict[str, float] | None = None, base: dict[str, Any] | None = None
) -> tuple[dict[str, Any], list[str]]:
    """thresholds.yaml + tuned overrides from the backend, with the browser's block 5 source.
    base: thresholds.yaml already read (it is parsed once per trip: slow in Pyodide), left untouched."""
    th = load_thresholds() if base is None else base
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


def _none_if_js_null(value: Any) -> Any:
    """A JS null handed over by the page -> None. Pyodide keeps null apart from undefined (JsNull, not
    None), so `x is None` alone lets it through: a frame without a face then failed in `_floats`."""
    return None if type(value).__name__ == "JsNull" else value


def _error_site(e: BaseException) -> str:
    """file:line of the innermost edge_agent frame of an error (code location only, no data)."""
    site = "?"
    for fs in traceback.extract_tb(e.__traceback__):
        filename = fs.filename.replace("\\", "/")  # Windows paths in tests, POSIX in Pyodide
        if "edge_agent" in filename:
            site = f"{filename.rsplit('edge_agent/', 1)[-1]}:{fs.lineno}"
    return site


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
        scenario: str = SIM,
        overrides: dict[str, float] | None = None,
        thresholds_version: int = 0,
    ) -> None:
        """thresholds_version: the version the page fetched `overrides` with (0 = none)."""
        if scenario not in SCENARIOS:
            raise ValueError(f"scenario must be one of {SCENARIOS}")
        base = load_thresholds()  # parsed once: also the base of thresholds reloaded during the trip
        th, self.problems = web_thresholds(overrides, base)
        applied = bool(overrides) and not self.problems
        self.versions = version_info(  # what this page runs, in every heartbeat and event (M41)
            thresholds_version if applied else 0, bundled_models(), thresholds_ignored=bool(self.problems)
        )
        self.device_id = device_id
        self.trip_id = trip_id
        self.extractor = FeatureExtractor(FeatureConfig.from_dict(th.get("features")))
        self.eye_state = EyeStateEstimator(EyeStateConfig.from_dict(th.get("eye_state")))
        self.phone_cfg = PhoneDetectorConfig.from_dict(th.get("phone"))
        self.preprocess_cfg = PreprocessConfig.from_dict(th.get("preprocess"))
        self.landmark_cfg = LandmarkConfig.from_dict(th.get("landmarks"))
        self.capture_cfg = CaptureConfig.from_dict(th.get("capture"))
        self.selector = DriverSelector(self.landmark_cfg)
        self.publisher_cfg = PublisherConfig.from_dict(th.get("publisher"))
        self.face_memory = FaceBoxMemory(self.phone_cfg.face_memory_s)
        ctx_cfg = ContextConfig.from_dict(th.get("context"))
        self.external: ExternalVehicle | None = None
        can: CanSimulator | ExternalVehicle
        if scenario == SIM:  # the page polls the simulator and calls vehicle_signal()
            self.external = ExternalVehicle(
                stale_s=ctx_cfg.vehicle_signal_stale_s,
                moving_kmh=ctx_cfg.min_speed_kmh,
                stationary_kmh=ctx_cfg.stationary_kmh,
            )
            can = self.external
        else:
            scenario_path = PROJECT_ROOT / "config" / "scenarios" / f"{scenario}.yaml"
            can = CanSimulator(load_scenario(scenario_path), moving_kmh=ctx_cfg.min_speed_kmh)
        self._phone: _PhoneResult | None = None
        self._records: list[dict[str, Any]] = []
        self._heartbeat: dict[str, Any] | None = None  # newest one not taken yet (M33)
        self._urgent = False  # an event that cannot wait for the page's send timer is queued
        # Thresholds changed on the dashboard during the trip (M47): the page polls, Python decides when.
        self._reloader = ThresholdReloader(web_thresholds(base=base)[0], self.versions["thresholds_version"])
        self.runtime = TripRuntime(th, trip_id, can, scenario, self.selector, emit=self._queue, versions=self.versions)
        self.hud = self.runtime.hud

    def _queue(self, kind: str, data: dict[str, Any]) -> None:
        if kind == "heartbeat":  # only the newest matters: never queued behind the records
            self._heartbeat = data
            return
        self._records.append({"kind": kind, "data": data})
        if kind == "event" and is_urgent(data):
            self._urgent = True  # the page sends it now instead of on its timer (M44)

    def settings(self) -> str:
        """What the browser side needs from thresholds.yaml (JSON): it keeps no thresholds of its own."""
        lm, ph, pub, cap = self.landmark_cfg, self.phone_cfg, self.publisher_cfg, self.capture_cfg
        return json.dumps(
            {
                "capture": {  # M71: the page's watch on its own loop
                    "frame_timeout_s": cap.frame_timeout_s,
                    "reconnect_interval_s": cap.reconnect_interval_s,
                    "camera_fps": cap.camera_fps,
                },
                "target_width": self.preprocess_cfg.target_width,
                "landmarks": {
                    "num_faces": lm.num_faces,
                    "min_face_detection_confidence": lm.min_face_detection_confidence,
                    "min_face_presence_confidence": lm.min_face_presence_confidence,
                    "min_tracking_confidence": lm.min_tracking_confidence,
                    "blendshapes": lm.blendshapes,
                },
                "phone": {
                    "input_size": ph.input_size,
                    "target_fps": ph.target_fps,
                    "num_threads": ph.num_threads,
                    "web_gpu": ph.web_gpu,  # M67: WebGPU where there is a real GPU, at its own rate
                    "gpu_target_fps": ph.web_gpu_target_fps,
                },
                "flush_interval_s": pub.flush_interval_s,
                "config_poll_s": pub.config_poll_s,
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

    def _phone_flag(self, face: tuple[float, float, float, float] | None, t: float) -> tuple[bool | None, str | None]:
        """(phone in the driver zone, how it is held); (None, None) when the YOLO result is too old."""
        result = self._phone
        if result is None or t - result.timestamp > self.phone_cfg.max_result_age_s:
            return None, None  # unknown, as on the device when YOLO is late
        dets = result.detections
        return phone_near_face(dets, face, self.phone_cfg), phone_kind(dets, face, self.phone_cfg)

    # ------------------------------------------------------------------ blocks 3 (numbers) -> 6, 5, 7-12, 13, 14
    def frame(self, t: float, *args: Any, **kwargs: Any) -> str:
        """One camera frame (see `_frame`). A frame that fails is caught: the loop goes on, and failing
        frames for hud.processing_error_s show "processing error" on the HUD (M28)."""
        try:
            args = tuple(_none_if_js_null(a) for a in args)
            kwargs = {k: _none_if_js_null(v) for k, v in kwargs.items()}
            return self._frame(t, *args, **kwargs)
        except Exception as e:  # noqa: BLE001 - one bad frame must not stop monitoring
            where = _error_site(e)
            if self.runtime.last_error != type(e).__name__:  # once per kind of error in a row
                print(f"[agent] frame failed at {where}\n{traceback.format_exc()}")  # browser console only
            return self._failed(t, type(e).__name__, where)

    def frame_error(self, t: float, error: str) -> str:
        """A frame failed in the page before it reached `frame` (MediaPipe, the canvas, the call into
        Python): the same path as a frame failing here, so frames failing for hud.processing_error_s
        are "processing error" on the HUD and `agent_error` to the backend (M71; they used to be a
        line in the browser console only). error: the error's class name, never data. Returns the HUD
        state like `frame`."""
        return self._failed(t, str(error), "page")

    def _failed(self, t: float, error: str, where: str) -> str:
        self.runtime.frame_failed(t, error)
        state = self.hud.to_json()
        state["measures"] = {"face": False, "ear": None, "mar": None, "yaw": None, "pitch": None, "phone": None}
        state["error"] = f"{error} · {where}"  # for "Chi tiết kỹ thuật" of #/live
        return json.dumps(state)

    def _frame(
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
        brow_up: Sequence[float] | None = None,
        scene_brightness: float | None = None,
        scene_contrast: float | None = None,
        sharpness: float | None = None,
    ) -> str:
        """One camera frame. points: num_faces x 478 x (x, y, z) in pixels (z scaled like x), or None
        without a face; eye_blink: (left, right) per face, in the same order; brow_up: MediaPipe
        browOuterUp (mean of both sides) per face, in the same order.

        channel_diff: mean |B - G|, |G - R| of the frame (block 2's IR test, 0 = grayscale / infrared).
        brightness: mean luminance 0-255 of the face (landmark box), of the frame without a face.
        scene_brightness / scene_contrast: mean and spread (std) of the whole frame's luminance;
        sharpness: Laplacian variance of the face (block 6 quality stage). None = not measured.
        Returns the HUD state (JSON), the same document the device's HUD server serves at /state.
        """
        lm = None
        if points is not None:
            faces = list(_floats(points).reshape(-1, NUM_LANDMARKS, 3))
            k = self.selector.choose(faces, width)  # 3: which face is the driver
            pts = faces[k]
            blinks = None if eye_blink is None else _floats(eye_blink)
            blink = None
            if blinks is not None and len(blinks) >= 2 * k + 2:
                blink = (float(blinks[2 * k]), float(blinks[2 * k + 1]))
            brows = None if brow_up is None else _floats(brow_up)
            brow = float(brows[k]) if brows is not None and len(brows) > k else None
            lm = FaceLandmarks(
                points=pts,
                image_width=width,
                image_height=height,
                face_conf=in_frame_ratio(pts, width, height),
                num_faces=max(num_faces, len(faces)),
                frame_id=frame_id,
                timestamp=t,
                eye_blink=blink,
                brow_up=brow,
            )
        face = self.face_memory.update(face_bbox(lm.points) if lm is not None else None, t)
        phone_flag, held = self._phone_flag(face, t)
        features = self.extractor(lm, frame_id, t)  # 6
        features = dataclasses.replace(  # 6: quality numbers measured by the page
            features,
            face_brightness=float(brightness) if lm is not None else None,
            scene_brightness=scene_brightness,
            scene_contrast=scene_contrast,
            sharpness=sharpness if lm is not None else None,
        )
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
        reload = self._reloader.take(self.runtime.parked)  # tuned thresholds, only while parked (M47)
        if reload is not None:
            self.runtime.apply_thresholds(reload.thresholds, reload.version, refused=not reload.applied)
        self.runtime.step(features, phone_flag, t, phone_kind=held)  # 10, 6 enrollment, 7-12, 13, 14
        state = self.hud.to_json()
        state["measures"] = {  # for the camera overlay of #/live
            "face": features.face_found,
            "ear": None if features.ear is None else round(features.ear, 3),
            "mar": None if features.mar is None else round(features.mar, 3),
            "yaw": None if features.yaw is None else round(features.yaw, 1),
            "pitch": None if features.pitch is None else round(features.pitch, 1),
            "phone": phone_flag,
        }
        state["flush"], self._urgent = self._urgent, False  # true: post the pending records now
        return json.dumps(state)

    # ------------------------------------------------------------------ HUD buttons, camera status
    def false_alarm(self, event_id: str) -> str:
        """The driver pressed "false alarm": 'ok', 'unknown', 'expired' or 'duplicate'."""
        return self.runtime.false_alarm(event_id)

    def camera(self, lost: bool) -> None:
        """The camera stopped giving frames / gives them again: the dashboard learns this driver is
        (not) monitored."""
        self.runtime.camera(lost)

    def camera_attempts(self, attempts: int) -> None:
        """The page asks for the lost camera again, for the `attempts`-th time ("Lần thử N" on the HUD)."""
        self.hud.set_incident_attempts(int(attempts))

    def hud_state(self) -> str:
        """The HUD state now (JSON), for the page to show between frames: while the camera is lost no
        frame brings it."""
        return json.dumps(self.hud.to_json())

    def expect_phone(self, expected: bool) -> None:
        """The page means to run the phone detector (it says so even when YOLO failed to load): frames
        without a fresh result are then watched and reported (M50). Off in builds that run without it."""
        self.runtime.phone_expected = bool(expected)

    def vehicle_signal(self, speed_kmh: float, turn_signal: str | None) -> None:
        """A reading of the driving simulator (tools/drive_sim.py), polled by the page. Without
        readings for context.vehicle_signal_stale_s the vehicle stands still at 0 km/h."""
        if self.external is not None:
            self.external.update(speed_kmh, turn_signal)

    def vehicle(self, action: str) -> str:
        """HUD buttons: "Đổi tài xế" ("change_driver"), the enrollment consent screen ("enroll_start" /
        "enroll_later"), the presence question ("presence_ok"): 'ok', 'ignored' (nothing was being asked), or 'unsupported'."""
        if action == "presence_ok":  # the tap on "Bạn còn ở đó không?" (M44)
            self.runtime.presence_answer()
            return "ok"
        if action in ("enroll_start", "enroll_later"):
            return "ok" if self.runtime.enrollment_answer(action == "enroll_start") else "ignored"
        if action != "change_driver":
            return "unsupported"
        self.runtime.change_driver()
        return "ok"

    def offer_thresholds(self, version: int, overrides: Any) -> bool:
        """What the backend now says this browser should run (the page asks every `config_poll_s`).
        Applied on a later frame, only while the vehicle is parked. True when it is a change."""
        if isinstance(overrides, str):  # the page hands the backend's `values` over as JSON
            overrides = json.loads(overrides)
        elif hasattr(overrides, "to_py"):
            overrides = overrides.to_py()
        return self._reloader.offer(int(version), {str(k): float(v) for k, v in dict(overrides or {}).items()})

    def end_trip(self) -> str:
        """The driver pressed "Kết thúc chuyến": the trip summary (JSON), also queued for the backend."""
        return json.dumps(self.runtime.end_trip())

    # ------------------------------------------------------------------ block 14 (the browser posts it)
    def idle(self, t: float) -> None:
        """Called on the page's send timer: the heartbeat goes on while no frame arrives (camera
        lost, page in the background), and says "stalled" then."""
        self.runtime.idle(t)

    def perf(self, doc: Any) -> bool:
        """The page's loop timings of the last seconds (JSON: frontend/src/live/perf.ts), sent with the
        next heartbeats (M49). False when nothing in it is usable; the heartbeat then goes without."""
        try:
            raw = json.loads(doc) if isinstance(doc, str) else doc
        except ValueError:
            raw = None
        self.runtime.perf = perf_record(raw)
        return self.runtime.perf is not None

    def take_heartbeat(self) -> str | None:
        """The newest heartbeat as a POST body of its own (JSON), or None. The page keeps only the
        latest one and sends it after the pending batches."""
        heartbeat, self._heartbeat = self._heartbeat, None
        if heartbeat is None:
            return None
        return json.dumps({"device_id": self.device_id, "heartbeat": heartbeat})

    def take_batch(self) -> str | None:
        """Pending records as one POST body (JSON), or None. The browser re-sends it on failure."""
        if not self._records:
            return None
        records, self._records = self._records[:MAX_RECORDS_PER_BATCH], self._records[MAX_RECORDS_PER_BATCH:]
        return json.dumps(batch_body(self.device_id, records))
