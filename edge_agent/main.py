"""DriverGuard edge agent: blocks 1-14 in one loop.

    python -m edge_agent.main --source 0       # default: manual vehicle, HUD buttons park / drive
    python -m edge_agent.main --source 0 --scenario config/scenarios/highway_night.yaml   # scripted CAN
    python -m edge_agent.main --source clip.mp4 --no-window     # headless, terminal only
    DG_DEVICE_KEY=dgk_... python -m edge_agent.main --source 0 --backend http://localhost:8100 --device-id cam-001

1 FrameSource -> 2 Preprocessor -> 3 FaceLandmarkDetector / 4 AsyncPhoneDetector (own thread)
-> 6 FeatureExtractor -> 7 drowsiness + 8 distraction (+ 10 CAN / context, 11 trip memory)
-> 9 risk engine -> 12 alert manager -> 13 HUD + 14 metadata publisher (enabled with --backend).
5 Eye-state CNN runs between 6 and 7, only on frames where EAR is not reliable (IR, dark, glare).

13 HUD: preview window, plus a local server on 127.0.0.1:--hud-port for the in-car HUD screen
    (frontend #/hud) with the "false alarm" button.
14: alerts, false-alarm feedback and one fatigue sample per minute go to the backend (batched,
    offline queue), and the trip summary when the trip ends. Thresholds tuned by engineers are fetched from the backend at startup.
End of trip: the driver presses "Kết thúc chuyến" on the HUD (POST /end-trip), or the agent
stops (q, end of video, Ctrl+C). Block 11 then builds the trip summary (alerts, fatigue per
minute, coverage, assessment, suggestions): it goes to the backend for the driver and the
higher roles, and back to the HUD, which shows it.
Vehicle (block 10 source): by default `manual` (config/scenarios/manual.yaml): the trip starts
parked (enrollment first), drives once the driver is enrolled, and the HUD buttons "Tạm dừng" /
"Tiếp tục lái" park / drive it. A scripted CAN scenario can be given with --scenario instead.
"Đổi tài xế" (any mode): park, drop the previous driver's baselines and block 3's face anchor,
the new driver enrolls; a driver_changed event goes to the backend.
Driver enrollment (block 6 stage): at the first stop the HUD guides the driver through three
short steps; once done, block 3 picks the driver among several faces by the enrolled face
signature, and blocks 7 / 8 use the driver's own baselines. Until then, everything runs on the
self-learnt baselines. A driver_enrolled event (duration, steps redone) goes to the backend.
Face lost while moving for risk.unavailable.no_face_s: monitoring unavailable (PRD FR-6), no
alert; the HUD shows it and monitoring_unavailable / monitoring_restored go to the backend.
Camera lost: block 1 keeps reopening it; meanwhile the HUD shows it and a camera_lost event
(camera_restored when frames come back) goes to the backend, so the dashboard knows this
vehicle is not monitored.

Frames live in RAM only: nothing here writes images to disk.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import cv2

from edge_agent.capture import CaptureConfig, FrameSource
from edge_agent.config import PROJECT_ROOT, load_thresholds
from edge_agent.context.can_sim import CanSimulator, ManualVehicle, is_manual, load_manual, load_scenario
from edge_agent.context.vehicle_context import ContextConfig
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.hud.hud import alert_line, draw_hud, enrollment_line, status_line, trip_summary_line
from edge_agent.hud.server import DEFAULT_ORIGINS, HudConfig, HudServer, HudState
from edge_agent.io.publisher import (
    MetadataPublisher,
    PublisherConfig,
    build_enrolled_event,
    build_event,
    build_sample,
    build_system_event,
    http_transport,
)
from edge_agent.io.remote_config import apply_overrides, fetch_thresholds
from edge_agent.perception import PreprocessConfig, Preprocessor
from edge_agent.perception.eye_state import EyeStateConfig, make_estimator
from edge_agent.perception.features import FeatureConfig, FeatureExtractor
from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
from edge_agent.perception.phone_detector import (
    AsyncPhoneDetector,
    FaceBoxMemory,
    PhoneDetectorConfig,
    face_bbox,
    phone_near_face,
)

WINDOW = "DriverGuard"
DEFAULT_SCENARIO = PROJECT_ROOT / "config" / "scenarios" / "manual.yaml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default="0", help="camera index (e.g. 0) or video file path")
    p.add_argument("--loop", action="store_true", help="loop the video file")
    p.add_argument("--config", default=None, help="path to thresholds.yaml")
    p.add_argument(
        "--scenario",
        default=str(DEFAULT_SCENARIO),
        help="vehicle: manual.yaml (HUD buttons, default) or a CAN scenario YAML (speed, turn signal)",
    )
    p.add_argument("--no-window", action="store_true", help="no preview window, terminal output only")
    p.add_argument("--no-phone", action="store_true", help="disable the YOLO phone detector")
    p.add_argument("--status-every", type=float, default=5.0, help="seconds between status lines (0 = off)")
    p.add_argument("--backend", default=None, help="backend base URL, e.g. http://localhost:8100 (off if omitted)")
    p.add_argument("--device-id", default="cam-001", help="this device's id, registered in the backend")
    p.add_argument("--device-key", default=None, help="device key (default: env DG_DEVICE_KEY)")
    p.add_argument("--hud-port", type=int, default=8765, help="local HUD server port on 127.0.0.1 (0 = off)")
    p.add_argument(
        "--hud-origin",
        action="append",
        default=[],
        help="extra web origin allowed to read the HUD server, e.g. https://driveguard-production-6b83.up.railway.app",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    th = load_thresholds(args.config)
    device_key = args.device_key or os.environ.get("DG_DEVICE_KEY", "")
    if args.backend and device_key:  # engineers' tuned thresholds override the local YAML
        remote = fetch_thresholds(args.backend, device_key)
        if remote is None:
            print("[config] backend unreachable: using local thresholds.yaml")
        elif remote:
            th, problems = apply_overrides(th, remote)
            print(f"[config] {len(remote)} tuned thresholds" + (f" IGNORED: {problems}" if problems else " applied"))

    source = FrameSource(args.source, CaptureConfig.from_dict(th.get("capture")), loop=args.loop)
    preprocessor = Preprocessor(PreprocessConfig.from_dict(th.get("preprocess")))
    landmarks = FaceLandmarkDetector(LandmarkConfig.from_dict(th.get("landmarks")))
    extractor = FeatureExtractor(FeatureConfig.from_dict(th.get("features")))
    eye_state = make_estimator(EyeStateConfig.from_dict(th.get("eye_state")))
    phone_cfg = PhoneDetectorConfig.from_dict(th.get("phone"))
    phone = None
    if not args.no_phone:
        try:
            phone = AsyncPhoneDetector(phone_cfg)
        except FileNotFoundError as e:
            print(f"[phone] disabled: {e}")

    moving_kmh = ContextConfig.from_dict(th.get("context")).min_speed_kmh
    manual: ManualVehicle | None = None
    can: CanSimulator | ManualVehicle
    if is_manual(args.scenario):
        manual = load_manual(args.scenario)
        manual.moving_kmh = moving_kmh
        can = manual
        scenario_name = "manual"
    else:
        scenario = load_scenario(args.scenario)
        can = CanSimulator(scenario, moving_kmh=moving_kmh)
        scenario_name = scenario.name
    decisions = DecisionPipeline(th)
    started_at = datetime.now(UTC)
    trip_id = datetime.now().strftime("trip-%Y%m%d-%H%M%S")
    publisher = None
    if args.backend:
        if not device_key:
            print("[publisher] disabled: no --device-key / DG_DEVICE_KEY")
        else:
            pub_cfg = PublisherConfig.from_dict(th.get("publisher"))
            transport = http_transport(args.backend, device_key, pub_cfg.timeout_s)
            publisher = MetadataPublisher(args.device_id, transport, pub_cfg)
            publisher.start()
            print(f"[publisher] {args.backend} as {args.device_id}, trip {trip_id}, {publisher.queued} queued")

    def on_false_alarm(event_id: str) -> None:
        print(f"[hud] driver marked alert {event_id[:8]} as a false alarm")
        if publisher is not None:
            publisher.publish_feedback(event_id)

    hud_state = HudState(HudConfig.from_dict(th.get("hud")))
    hud_server = None
    if args.hud_port:
        try:
            hud_server = HudServer(
                hud_state, on_false_alarm, port=args.hud_port, allowed_origins=(*DEFAULT_ORIGINS, *args.hud_origin)
            ).start()
            print(f"[hud] in-car HUD server on http://127.0.0.1:{hud_server.port}/state")
        except OSError as e:
            print(f"[hud] server disabled: {e}")
    print(f"[main] source={args.source} scenario={scenario_name} ({Path(args.scenario).name})")
    if manual is not None:
        hud_state.set_vehicle(manual.state())

    if not args.no_window:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    if phone is not None:
        phone.start()

    fps, last_t, last_status = 0.0, time.monotonic(), 0.0
    face_memory = FaceBoxMemory(phone_cfg.face_memory_s)  # driver zone survives a phone hiding the face
    t0: float | None = None
    bins_sent, minute_max_level = 0, 0
    camera_lost, last_speed = False, None
    unavailable = False
    lost_since: float | None = None  # monotonic time the camera was lost
    camera_lost_s = 0.0

    def report_camera(lost: bool) -> None:
        nonlocal lost_since, camera_lost_s
        reason = "camera_lost" if lost else "camera_restored"
        print(
            f"[camera] {'LOST: driver not monitored, reconnecting' if lost else 'back'} ({source.reconnects} reconnects)"
        )
        hud_state.set_camera_lost(lost)
        if lost:
            lost_since = time.monotonic()
        elif lost_since is not None:
            camera_lost_s += time.monotonic() - lost_since
            lost_since = None
        if publisher is not None:
            publisher.publish(build_system_event(reason, trip_id, last_speed))

    try:
        with source, landmarks:
            while True:
                if hud_state.end_requested:  # "Kết thúc chuyến" on the HUD
                    print("[main] trip ended from the HUD")
                    break
                frame = source.read(timeout=0.5)
                if source.lost != camera_lost:  # 1: camera unplugged / back
                    camera_lost = not camera_lost
                    report_camera(camera_lost)
                if frame is None:
                    if source.ended:
                        print("[main] end of stream")
                        break
                    continue
                if t0 is None:
                    t0 = frame.timestamp

                pre = preprocessor(frame)  # 2
                lm = landmarks.detect(pre)  # 3
                phone_flag = None
                face = face_memory.update(face_bbox(lm.points) if lm is not None else None, pre.timestamp)
                if phone is not None:  # 4, own thread; reuse the latest result
                    phone.submit(pre)
                    result = phone.latest()
                    if result is not None:
                        phone_flag = phone_near_face(result.detections, face, phone_cfg)
                features = extractor(lm, pre.frame_id, pre.timestamp)  # 6
                if eye_state is not None:  # 5, only when EAR is not reliable
                    features = eye_state(pre, lm, features)
                for action in hud_state.take_actions():  # 13: HUD buttons
                    if action == "change_driver":
                        print("[main] driver change: the new driver enrolls")
                        if manual is not None:
                            manual.change_driver()
                        decisions.change_driver()
                        landmarks.selector.set_anchor(None)
                        if publisher is not None:
                            publisher.publish(build_system_event("driver_changed", trip_id, last_speed))
                    elif manual is not None:
                        manual.park() if action == "park" else manual.drive()
                        print(f"[main] vehicle: {'parked' if action == 'park' else 'driving'}")
                signals = can.sample(frame.timestamp - t0)  # 10 (CAN)
                last_speed = signals.speed_kmh
                r = decisions.step(features, phone_flag, signals)  # 6 enrollment, 7, 8, 10, 11, 9, 12
                if manual is not None:
                    manual.on_enrollment(r.enrollment.events)  # enrolled: start driving
                    hud_state.set_vehicle(manual.state())
                if r.enrollment.events:
                    print(f"t={signals.t:7.1f}s  {enrollment_line(r) or '[ENROLL] done'}")
                if r.risk.unavailable != unavailable:  # 9: face lost while moving / back (FR-6)
                    unavailable = r.risk.unavailable
                    reason = "monitoring_unavailable" if unavailable else "monitoring_restored"
                    print(f"t={signals.t:7.1f}s  [MONITOR] {'unavailable: no face' if unavailable else 'restored'}")
                    if publisher is not None:
                        publisher.publish(build_system_event(reason, trip_id, last_speed))
                if "enrolled" in r.enrollment.events and r.enrollment.profile is not None:
                    landmarks.selector.set_anchor(r.enrollment.profile.anchor)  # 3: who the driver is
                    if publisher is not None:
                        publisher.publish(build_enrolled_event(r, trip_id))

                now = time.monotonic()
                dt, last_t = now - last_t, now
                if dt > 0:
                    fps = 1.0 / dt if fps == 0 else 0.9 * fps + 0.1 / dt

                hud_state.update(r, fps)  # 13
                minute_max_level = max(minute_max_level, r.alert.active_level)
                if r.alert.new_alert is not None:  # 13, 14
                    event = build_event(r.alert.new_alert, r, trip_id)
                    hud_state.add_alert(event["event_id"], r.alert.new_alert.level, r.alert.new_alert.reasons)
                    print(f"t={signals.t:7.1f}s  {alert_line(r.alert.new_alert)}")
                    if publisher is not None:
                        publisher.publish(event)
                if r.trip.bins_completed > bins_sent:  # a minute just closed: one fatigue timeline point
                    bins_sent = r.trip.bins_completed
                    if publisher is not None and r.trip.minute_scores:
                        publisher.publish_sample(
                            build_sample(r.trip.minute_scores[-1], r.drowsiness.perclos_60s, minute_max_level, trip_id)
                        )
                    minute_max_level = r.alert.active_level
                if args.status_every > 0 and now - last_status >= args.status_every:
                    last_status = now
                    net = ""
                    if publisher is not None:
                        net = f" | sent {publisher.sent} queued {publisher.queued}" + (
                            " OFFLINE" if publisher.online is False else ""
                        )
                    if phone is not None and phone.stale_results:  # phone detection too slow to count
                        net += f" | phone stale {phone.stale_results}/{phone.runs}"
                    print(f"t={signals.t:7.1f}s  {status_line(r, fps)}{net}")
                if not args.no_window:
                    cv2.imshow(WINDOW, draw_hud(pre.image, r, fps))
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                        break
    except KeyboardInterrupt:
        print("[main] interrupted")
    finally:
        if t0 is not None:  # 11: the trip summary, for the backend and the HUD
            if lost_since is not None:
                camera_lost_s += time.monotonic() - lost_since
            summary = decisions.trip_log.summary(
                trip_id,
                started_at,
                datetime.now(UTC),
                false_alarms=hud_state.false_alarms,
                camera_lost_s=camera_lost_s,
            ).to_dict()
            print(f"[trip] {trip_summary_line(summary)}")
            if publisher is not None:
                publisher.publish_summary(summary)
            hud_state.set_summary(summary)
            if hud_state.end_requested and hud_server is not None:
                hud_state.wait_delivered(3.0)  # let the HUD get it before the server stops
        if hud_server is not None:
            hud_server.stop()
        if phone is not None:
            phone.stop()
        if publisher is not None:
            publisher.stop()  # final flush; anything unsent stays in the outbox for next start
            print(f"[publisher] sent {publisher.sent}, still queued {publisher.queued}, dropped {publisher.dropped}")
        if not args.no_window:
            cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    sys.exit(main())
