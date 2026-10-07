"""M49: the loop's own timings ride on the heartbeat (numbers only), and the web benchmark's input."""

import json
import math

import numpy as np

from backend.schemas import EventBatch
from edge_agent.io.publisher import build_heartbeat, perf_record
from edge_agent.perception.features import POSE_LANDMARKS
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import run, synthetic_face
from tools import bench_web

PERF = {
    "samples": 300,
    "stages_ms": {
        "camera_lag": {"p50": 40.0, "p95": 55.0, "max": 90.0},
        "capture": {"p50": 1.2, "p95": 2.04, "max": 9.0},
        "landmarks": {"p50": 8.0, "p95": 11.0, "max": 30.0},
        "python": {"p50": 0.6, "p95": 0.9, "max": 4.0},
        "total": {"p50": 10.5, "p95": 14.0, "max": 41.0},
        "yolo": {"p50": 166.0, "p95": 170.0, "max": 181.0},
        "yolo_age": {"p50": 250.0, "p95": 340.0, "max": 380.0},
    },
    "landmarks_delegate": "GPU",
    "gpu": "hardware",
    "yolo_threads": 1,
    "camera_delivered": 303,
    "camera_dropped": 3,
}


def test_perf_record_keeps_known_stages_rounded():
    got = perf_record(PERF)
    assert got is not None
    assert got["stages_ms"]["capture"] == {"p50": 1.2, "p95": 2.0, "max": 9.0}
    assert set(got["stages_ms"]) == set(PERF["stages_ms"])
    assert (got["samples"], got["landmarks_delegate"], got["yolo_threads"]) == (300, "GPU", 1)
    assert (got["camera_delivered"], got["camera_dropped"]) == (303, 3)
    assert got["gpu"] == "hardware"
    assert got["yolo_provider"] is None  # a page older than M67 does not say


def test_perf_record_says_where_the_phone_detector_runs():
    """M67: WebGPU or wasm; anything else is dropped so the backend never refuses the heartbeat."""
    assert perf_record({**PERF, "yolo_provider": "webgpu"})["yolo_provider"] == "webgpu"
    assert perf_record({**PERF, "yolo_provider": "wasm"})["yolo_provider"] == "wasm"
    assert perf_record({**PERF, "yolo_provider": "cuda"})["yolo_provider"] is None


def test_perf_record_drops_what_the_backend_would_refuse():
    raw = {
        **PERF,
        "stages_ms": {
            **PERF["stages_ms"],
            "gpu_upload": {"p50": 1, "p95": 2, "max": 3},  # not a stage the backend knows
            "python": {"p50": math.nan, "p95": 1, "max": 2},  # not a number
            "yolo": {"p50": 1, "p95": 2},  # incomplete
            "total": {"p50": 1, "p95": 2, "max": 1e9},  # out of range
        },
        "landmarks_delegate": "NPU",
        "gpu": "quantum",
        "yolo_threads": 0,
        "camera_dropped": -1,
        "image": "data:...",  # anything else is not carried over
    }
    got = perf_record(raw)
    assert got is not None
    assert set(got["stages_ms"]) == {"camera_lag", "capture", "landmarks", "yolo_age"}
    assert got["landmarks_delegate"] is None and got["yolo_threads"] is None and got["camera_dropped"] is None
    assert got["gpu"] is None
    assert "image" not in got


def test_perf_record_is_none_without_anything_usable():
    for raw in (None, "fast", [], {}, {"samples": 0, "stages_ms": PERF["stages_ms"]}, {"samples": 10, "stages_ms": {}}):
        assert perf_record(raw) is None


def test_heartbeat_with_perf_is_accepted_by_the_backend_schema():
    beat = build_heartbeat("monitoring", "trip-1", True, perf=perf_record(PERF))
    batch = EventBatch.model_validate({"device_id": "web-an", "heartbeat": beat})
    assert batch.heartbeat is not None and batch.heartbeat.perf is not None
    assert batch.heartbeat.perf.stages_ms["total"].p95 == 14.0
    assert "perf" not in build_heartbeat("monitoring", "trip-1", True)  # nothing measured: left out


def test_page_timings_go_out_with_the_next_heartbeat():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    _, t, f = run(agent, 2, points=synthetic_face())
    assert "perf" not in json.loads(agent.take_heartbeat())["heartbeat"]  # the page has not reported yet
    assert agent.perf(json.dumps(PERF)) is True
    run(agent, 31, t0=t, frame0=f, points=synthetic_face())  # the next periodic heartbeat
    beat = json.loads(agent.take_heartbeat())["heartbeat"]
    assert beat["perf"]["stages_ms"]["python"] == {"p50": 0.6, "p95": 0.9, "max": 4.0}
    assert beat["perf"]["landmarks_delegate"] == "GPU"


def test_unusable_page_timings_never_reach_the_heartbeat():
    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    assert agent.perf("not json") is False
    assert agent.perf(json.dumps({"samples": 5})) is False
    run(agent, 2, points=synthetic_face())
    assert "perf" not in json.loads(agent.take_heartbeat())["heartbeat"]


# ---------------------------------------------------------------------------- tools/bench_web.py
def test_bench_sequence_is_a_moving_face_with_blinks():
    frames = bench_web.moving_faces(seconds=10, fps=30)
    assert len(frames) == 300 and all(len(f["points"]) == 478 * 3 for f in frames)
    pose = np.array([np.asarray(f["points"]).reshape(478, 3)[list(POSE_LANDMARKS), :2] for f in frames])
    assert np.ptp(pose[:, -1, 0]) > 20  # the cheek edge travels: the head-pose fit has work on every frame
    closed = [f["blink"][0] > 0.5 for f in frames]
    assert 0 < sum(closed) < 30 and not closed[0]
    assert frames == bench_web.moving_faces(seconds=10, fps=30)  # same numbers on every run


def test_bench_report_has_one_row_per_run_with_the_ratio():
    run_ = {
        "date": "06/10/2026",
        "machine": "arm64, Darwin",
        "input": "synthetic moving face, 60 s at 30 FPS",
        "native": {"mean_ms": 0.15, "p50_ms": 0.15, "p95_ms": 0.2, "p99_ms": 0.3, "max_ms": 1.0},
        "pyodide": {
            "p50_ms": 0.6,
            "p95_ms": 0.9,
            "max_ms": 3.0,
            "startup_ms": 1100.0,
            "shares": {"head_pose_solve_pnp": 0.5},
            "project_calls_per_frame": 9.8,
        },
        "software": {"Python": "3.12", "Pyodide": "0.29.3"},
    }
    text = bench_web.report({"before": run_, "after": run_})
    rows = [line for line in text.splitlines() if line.startswith("| before") or line.startswith("| after")]
    assert len(rows) == 2
    assert "| 0.15 / 0.20 | 0.60 / 0.90 / 3.0 | 4.0x | 50 % | 9.8 | 1100 |" in rows[0]
