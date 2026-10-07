"""M45: the browser build ships no OpenCV. The whole in-browser agent must import and run with `cv2`
missing, and give the same numbers as with it."""

import json
import subprocess
import sys
import textwrap

from edge_agent.config import PROJECT_ROOT
from edge_agent.web.bridge import WebAgent
from tests.test_edge_agent.test_web_bridge import FPS, H, W, synthetic_face

SCRIPT = textwrap.dedent(
    """
    import json, sys
    sys.modules["cv2"] = None          # `import cv2` now raises ImportError, as in Pyodide without the package
    import numpy as np
    from edge_agent.web.bridge import WebAgent
    from edge_agent.perception.phone_detector import decode_yolov8
    from tests.test_edge_agent.test_web_bridge import synthetic_face, W, H, FPS
    assert "cv2" not in {k for k, v in sys.modules.items() if v is not None}

    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")
    out = []
    for i in range(int(6 * FPS)):
        t = i / FPS
        face = synthetic_face(ear=0.06 if t >= 3 else 0.30).ravel()
        blink = (0.9, 0.9) if t >= 3 else (0.05, 0.05)
        s = json.loads(agent.frame(t, i, W, H, face, 1, blink, 12.0, 140.0))
        out.append([s["level"], s["measures"]["yaw"], s["measures"]["pitch"], s["measures"]["ear"]])
    assert "error" not in s, s.get("error")
    raw = np.zeros((1, 84, 4), np.float32)
    raw[0, :4, 0] = raw[0, :4, 1] = (320, 240, 80, 120)
    raw[0, 4 + 67, :2] = (0.9, 0.8)   # two boxes on the same phone
    raw[0, :4, 2] = (100, 100, 40, 60)
    raw[0, 4 + 67, 2] = 0.7
    dets = decode_yolov8(raw, 67, 0.35, 0.45, 1.0, (0, 0), (640, 480))
    print(json.dumps({"frames": out, "phones": [[round(v, 3) for v in d.bbox] + [round(d.score, 3)] for d in dets]}))
    """
)


def test_in_browser_agent_runs_without_opencv_and_agrees_with_it():
    run = subprocess.run(
        [sys.executable, "-c", SCRIPT], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=120, check=False
    )
    assert run.returncode == 0, run.stderr[-2000:]
    got = json.loads(run.stdout.strip().splitlines()[-1])

    agent = WebAgent("web-an", "trip-web-1", scenario="highway_night")  # this process has OpenCV
    want = []
    for i in range(int(6 * FPS)):
        t = i / FPS
        face = synthetic_face(ear=0.06 if t >= 3 else 0.30).ravel()
        blink = (0.9, 0.9) if t >= 3 else (0.05, 0.05)
        s = json.loads(agent.frame(t, i, W, H, face, 1, blink, 12.0, 140.0))
        want.append([s["level"], s["measures"]["yaw"], s["measures"]["pitch"], s["measures"]["ear"]])
    assert [f[0] for f in got["frames"]] == [f[0] for f in want]  # same levels on every frame
    assert max(f[0] for f in want) == 3  # ... and the run does reach the microsleep alarm
    for a, b in zip(got["frames"], want, strict=True):
        assert abs(a[1] - b[1]) <= 0.1 and abs(a[2] - b[2]) <= 0.1 and a[3] == b[3]  # degrees, EAR
    assert len(got["phones"]) == 2 and got["phones"][0][-1] == 0.9  # the duplicate box was suppressed
