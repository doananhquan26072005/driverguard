"""DriverGuard edge agent: blocks 1-14 in one loop.

    python -m edge_agent.main --source 0       # vehicle from tools/drive_sim.py (none running = parked)
    python tools/drive_sim.py                  # in another terminal: accelerate, brake, turn signals
    python -m edge_agent.main --source 0 --scenario config/scenarios/highway_night.yaml   # scripted CAN
    python -m edge_agent.main --source clip.mp4 --no-window     # headless, terminal only
    DG_DEVICE_KEY=dgk_... python -m edge_agent.main --source 0 --backend http://localhost:8100 --device-id cam-001

1 FrameSource -> 2 Preprocessor -> 3 FaceLandmarkDetector / 4 AsyncPhoneDetector (own thread)
-> 6 FeatureExtractor -> 7 drowsiness + 8 distraction (+ 10 CAN / context, 11 trip memory)
-> 9 risk engine -> 12 alert manager -> 13 HUD + 14 metadata publisher (enabled with --backend).
5 Eye-state CNN runs between 6 and 7, only on frames where EAR is not reliable (IR, dark, glare).
From the features on, edge_agent.runtime.TripRuntime (shared with the browser's #/live) runs
blocks 6-12, keeps the HUD state and builds the block 14 records; this file is the device's I/O.

13 HUD: preview window, plus a local server on 127.0.0.1:--hud-port for the in-car HUD screen
    (frontend #/hud) with the "false alarm" button.
14: alerts, false-alarm feedback and one fatigue sample per minute go to the backend (batched,
    offline queue), and the trip summary when the trip ends. Thresholds tuned by engineers are fetched from the backend at startup.
End of trip: the driver presses "Kết thúc chuyến" on the HUD (POST /end-trip), or the agent
stops (q, end of video, Ctrl+C). Block 11 then builds the trip summary (alerts, fatigue per
minute, coverage, assessment, suggestions): it goes to the backend for the driver and the
higher roles, and back to the HUD, which shows it.
Vehicle (block 10 source): by default speed and turn signal come from the driving simulator
(tools/drive_sim.py, polled on --sim-url); 0 km/h = stopped / parked, and with no simulator
running the vehicle stands still at 0 km/h. A scripted CAN scenario can be given with --scenario
instead. "Đổi tài xế" on the HUD: drop the previous driver's baselines and block 3's face
anchor, the new driver enrolls; a driver_changed event goes to the backend.
Driver enrollment (block 6 stage): at the first stop the HUD guides the driver through three
short steps; once done, block 3 picks the driver among several faces by the enrolled face
signature, and blocks 7 / 8 use the driver's own baselines. Until then, everything runs on the
self-learnt baselines. A driver_enrolled event (duration, steps redone) goes to the backend.
Face lost while moving for risk.unavailable.no_face_s: monitoring unavailable (PRD FR-6), no
alert; the HUD shows it and monitoring_unavailable / monitoring_restored go to the backend.
A frame that fails in blocks 2-14 is caught: the loop goes on, and failing frames for
hud.processing_error_s show "processing error" on the HUD and send agent_error (M28).
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
from datetime import datetime
from pathlib import Path

import cv2

from edge_agent.capture import CaptureConfig, FrameSource
from edge_agent.config import load_thresholds
from edge_agent.context.can_sim import (
    DEFAULT_SIM_URL,
    SIM,
    CanSimulator,
    ExternalVehicle,
    SignalLink,
    load_scenario,
)
from edge_agent.context.vehicle_context import ContextConfig
from edge_agent.hud.hud import alert_line, draw_hud, enrollment_line, status_line, trip_summary_line
from edge_agent.hud.server import DEFAULT_ORIGINS, HudServer
from edge_agent.io.publisher import MetadataPublisher, PublisherConfig, http_transport
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
from edge_agent.runtime import TripRuntime

WINDOW = "DriverGuard"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default="0", help="camera index (e.g. 0) or video file path")
    p.add_argument("--loop", action="store_true", help="loop the video file")
    p.add_argument("--config", default=None, help="path to thresholds.yaml")
    p.add_argument(
        "--scenario",
        default=None,
        help="scripted CAN scenario YAML (speed, turn signal) instead of the driving simulator",
    )
    p.add_argument("--sim-url", default=DEFAULT_SIM_URL, help="driving simulator endpoint (tools/drive_sim.py)")
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
    if not args.hud_port and th.get("enrollment", {}).get("require_consent", True):
        # No HUD: nobody can read the consent screen or answer it, so the steps start as before.
        th["enrollment"] = {**th.get("enrollment", {}), "require_consent": False}
        print("[enroll] no HUD: enrollment starts without the consent screen")

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

    ctx_cfg = ContextConfig.from_dict(th.get("context"))
    moving_kmh = ctx_cfg.min_speed_kmh
    link: SignalLink | None = None
    can: CanSimulator | ExternalVehicle
    if args.scenario is None:
        external = ExternalVehicle(
            stale_s=ctx_cfg.vehicle_signal_stale_s, moving_kmh=moving_kmh, stationary_kmh=ctx_cfg.stationary_kmh
        )
        link = SignalLink(external, args.sim_url).start()
        can, scenario_name = external, SIM
    else:
        scenario = load_scenario(args.scenario)
        can = CanSimulator(scenario, moving_kmh=moving_kmh)
        scenario_name = scenario.name

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

    runtime = TripRuntime(
        th, trip_id, can, scenario_name, landmarks.selector, emit=publisher.publish_record if publisher else None
    )
    hud_state = runtime.hud

    def on_false_alarm(event_id: str) -> None:  # already marked on hud_state by the HUD server
        print(f"[hud] driver marked alert {event_id[:8]} as a false alarm")
        runtime.record_feedback(event_id)

    hud_server = None
    if args.hud_port:
        try:
            hud_server = HudServer(
                hud_state, on_false_alarm, port=args.hud_port, allowed_origins=(*DEFAULT_ORIGINS, *args.hud_origin)
            ).start()
            print(f"[hud] in-car HUD server on http://127.0.0.1:{hud_server.port}/state")
        except OSError as e:
            print(f"[hud] server disabled: {e}")
    vehicle_from = args.sim_url if args.scenario is None else Path(args.scenario).name
    print(f"[main] source={args.source} vehicle={scenario_name} ({vehicle_from})")

    if not args.no_window:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    if phone is not None:
        phone.start()

    last_status = 0.0
    face_memory = FaceBoxMemory(phone_cfg.face_memory_s)  # driver zone survives a phone hiding the face
    camera_lost = False

    try:
        with source, landmarks:
            while True:
                if hud_state.end_requested:  # "Kết thúc chuyến" on the HUD
                    print("[main] trip ended from the HUD")
                    break
                frame = source.read(timeout=0.5)
                if source.lost != camera_lost:  # 1: camera unplugged / back
                    camera_lost = not camera_lost
                    state = "LOST: driver not monitored, reconnecting" if camera_lost else "back"
                    print(f"[camera] {state} ({source.reconnects} reconnects)")
                    runtime.camera(camera_lost)
                if frame is None:
                    if source.ended:
                        print("[main] end of stream")
                        break
                    runtime.idle(time.monotonic())  # 14: heartbeat goes on without frames
                    continue

                try:
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
                            runtime.change_driver()
                        elif action in ("enroll_start", "enroll_later"):  # enrollment consent screen
                            agree = action == "enroll_start"
                            if runtime.enrollment_answer(agree):
                                print(f"[main] enrollment: driver {'agreed' if agree else 'said later'}")
                    now = time.monotonic()
                    step = runtime.step(features, phone_flag, frame.timestamp, clock=now)  # 10, 6-12, 13, 14
                except Exception as e:  # noqa: BLE001 - one bad frame must not stop monitoring (M28)
                    if runtime.last_error != type(e).__name__:  # once per kind of error in a row
                        print(f"[main] frame failed: {type(e).__name__}: {e}")  # local log only, never sent
                    runtime.frame_failed(frame.timestamp, type(e).__name__, clock=time.monotonic())
                    continue
                r, signals, fps = step.result, step.signals, runtime.fps
                if r.enrollment.events:
                    print(f"t={signals.t:7.1f}s  {enrollment_line(r) or '[ENROLL] done'}")
                if step.unavailable_changed:  # 9: face lost while moving / back (FR-6)
                    print(
                        f"t={signals.t:7.1f}s  [MONITOR] {'unavailable: no face' if r.risk.unavailable else 'restored'}"
                    )
                if r.alert.new_alert is not None:
                    print(f"t={signals.t:7.1f}s  {alert_line(r.alert.new_alert)}")
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
        if runtime.started:  # 11: the trip summary, for the backend and the HUD
            summary = runtime.end_trip()
            print(f"[trip] {trip_summary_line(summary)}")
            hud_state.set_summary(summary)
            if hud_state.end_requested and hud_server is not None:
                hud_state.wait_delivered(3.0)  # let the HUD get it before the server stops
        if hud_server is not None:
            hud_server.stop()
        if link is not None:
            link.stop()
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
