"""DriverGuard edge agent: blocks 1-14 in one loop (block 5 excluded).

    python -m edge_agent.main --source 0 --scenario config/scenarios/highway_night.yaml
    python -m edge_agent.main --source clip.mp4 --no-window     # headless, terminal only
    DG_DEVICE_KEY=dgk_... python -m edge_agent.main --source 0 --backend http://localhost:8100 --device-id cam-001

1 FrameSource -> 2 Preprocessor -> 3 FaceLandmarkDetector / 4 AsyncPhoneDetector (own thread)
-> 6 FeatureExtractor -> 7 drowsiness + 8 distraction (+ 10 CAN / context, 11 trip memory)
-> 9 risk engine -> 12 alert manager -> 13 HUD + 14 metadata publisher (alerts only, batched,
offline queue; enabled with --backend). Block 5 (eye-state CNN) is a later milestone.

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
from edge_agent.config import PROJECT_ROOT, load_thresholds
from edge_agent.context.can_sim import CanSimulator, load_scenario
from edge_agent.decision.pipeline import DecisionPipeline
from edge_agent.hud.hud import alert_line, draw_hud, status_line
from edge_agent.io.publisher import MetadataPublisher, PublisherConfig, build_event, http_transport
from edge_agent.perception import PreprocessConfig, Preprocessor
from edge_agent.perception.features import FeatureConfig, FeatureExtractor
from edge_agent.perception.landmarks import FaceLandmarkDetector, LandmarkConfig
from edge_agent.perception.phone_detector import AsyncPhoneDetector, PhoneDetectorConfig, face_bbox, phone_near_face

WINDOW = "DriverGuard"
DEFAULT_SCENARIO = PROJECT_ROOT / "config" / "scenarios" / "city_day.yaml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", default="0", help="camera index (e.g. 0) or video file path")
    p.add_argument("--loop", action="store_true", help="loop the video file")
    p.add_argument("--config", default=None, help="path to thresholds.yaml")
    p.add_argument("--scenario", default=str(DEFAULT_SCENARIO), help="CAN scenario YAML (speed, turn signal)")
    p.add_argument("--no-window", action="store_true", help="no preview window, terminal output only")
    p.add_argument("--no-phone", action="store_true", help="disable the YOLO phone detector")
    p.add_argument("--status-every", type=float, default=5.0, help="seconds between status lines (0 = off)")
    p.add_argument("--backend", default=None, help="backend base URL, e.g. http://localhost:8100 (off if omitted)")
    p.add_argument("--device-id", default="cam-001", help="this device's id, registered in the backend")
    p.add_argument("--device-key", default=None, help="device key (default: env DG_DEVICE_KEY)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    th = load_thresholds(args.config)

    source = FrameSource(args.source, CaptureConfig.from_dict(th.get("capture")), loop=args.loop)
    preprocessor = Preprocessor(PreprocessConfig.from_dict(th.get("preprocess")))
    landmarks = FaceLandmarkDetector(LandmarkConfig.from_dict(th.get("landmarks")))
    extractor = FeatureExtractor(FeatureConfig.from_dict(th.get("features")))
    phone_cfg = PhoneDetectorConfig.from_dict(th.get("phone"))
    phone = None
    if not args.no_phone:
        try:
            phone = AsyncPhoneDetector(phone_cfg)
        except FileNotFoundError as e:
            print(f"[phone] disabled: {e}")

    scenario = load_scenario(args.scenario)
    can = CanSimulator(scenario, moving_kmh=float((th.get("context") or {}).get("min_speed_kmh", 5.0)))
    decisions = DecisionPipeline(th)
    trip_id = datetime.now().strftime("trip-%Y%m%d-%H%M%S")
    publisher = None
    if args.backend:
        key = args.device_key or os.environ.get("DG_DEVICE_KEY", "")
        if not key:
            print("[publisher] disabled: no --device-key / DG_DEVICE_KEY")
        else:
            pub_cfg = PublisherConfig.from_dict(th.get("publisher"))
            publisher = MetadataPublisher(args.device_id, http_transport(args.backend, key, pub_cfg.timeout_s), pub_cfg)
            publisher.start()
            print(f"[publisher] {args.backend} as {args.device_id}, trip {trip_id}, {publisher.queued} queued")
    print(f"[main] source={args.source} scenario={scenario.name} ({Path(args.scenario).name})")

    if not args.no_window:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
    if phone is not None:
        phone.start()

    fps, last_t, last_status = 0.0, time.monotonic(), 0.0
    t0: float | None = None
    try:
        with source, landmarks:
            while True:
                frame = source.read(timeout=2.0)
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
                if phone is not None:  # 4, own thread; reuse the latest result
                    phone.submit(pre)
                    result = phone.latest()
                    if result is not None:
                        face = face_bbox(lm.points) if lm is not None else None
                        phone_flag = phone_near_face(result.detections, face, phone_cfg)
                features = extractor(lm, pre.frame_id, pre.timestamp)  # 6
                signals = can.sample(frame.timestamp - t0)  # 10 (CAN)
                r = decisions.step(features, phone_flag, signals)  # 7, 8, 10, 11, 9, 12

                now = time.monotonic()
                dt, last_t = now - last_t, now
                if dt > 0:
                    fps = 1.0 / dt if fps == 0 else 0.9 * fps + 0.1 / dt

                if r.alert.new_alert is not None:  # 13, 14
                    print(f"t={signals.t:7.1f}s  {alert_line(r.alert.new_alert)}")
                    if publisher is not None:
                        publisher.publish(build_event(r.alert.new_alert, r, trip_id))
                if args.status_every > 0 and now - last_status >= args.status_every:
                    last_status = now
                    net = ""
                    if publisher is not None:
                        net = f" | sent {publisher.sent} queued {publisher.queued}" + (
                            " OFFLINE" if publisher.online is False else ""
                        )
                    print(f"t={signals.t:7.1f}s  {status_line(r, fps)}{net}")
                if not args.no_window:
                    cv2.imshow(WINDOW, draw_hud(pre.image, r, fps))
                    key = cv2.waitKey(1) & 0xFF
                    if key in (ord("q"), 27) or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                        break
    except KeyboardInterrupt:
        print("[main] interrupted")
    finally:
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
