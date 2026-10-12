"""Write frontend/src/lib/defaults.gen.json: the numbers of config/thresholds.yaml that the web
pages need before, or without, an agent to hand them over.

While a trip runs the agent sends its own (thresholds.yaml plus what engineers tuned on the
dashboard): the HUD state carries `display`, the page's loop reads `WebAgent.settings()`. This file
is what the same pages use until the first state arrives, in the scripted demo, on the dashboard and
on the driving controls. It is checked in; tests/test_edge_agent/test_m85_no_hardcode.py fails when
it no longer matches thresholds.yaml.

    python tools/web_defaults.py            # rewrite the file
    python tools/web_defaults.py --check    # exit 1 when it is out of date
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from edge_agent.capture.frame_source import CaptureConfig  # noqa: E402
from edge_agent.config import load_thresholds  # noqa: E402
from edge_agent.context.vehicle_context import ContextConfig  # noqa: E402
from edge_agent.hud.server import HudConfig, hud_display  # noqa: E402

DEST = ROOT / "frontend" / "src" / "lib" / "defaults.gen.json"


def web_defaults(thresholds: dict[str, Any] | None = None) -> dict[str, Any]:
    """The numbers of thresholds.yaml that the web pages need before, or without, an agent."""
    th = load_thresholds() if thresholds is None else thresholds
    cap = CaptureConfig.from_dict(th.get("capture"))
    ctx = ContextConfig.from_dict(th.get("context"))
    return {
        "hud": {**hud_display(th), "trend_minutes": HudConfig.from_dict(th.get("hud")).trend_minutes},
        "camera": {"width": cap.web_camera_width, "height": cap.web_camera_height, "fps": cap.camera_fps},
        "vehicle": {
            "poll_s": ctx.vehicle_poll_s,
            "send_s": ctx.vehicle_send_s,
            "stale_s": ctx.vehicle_signal_stale_s,
        },
    }


def render(thresholds: dict[str, Any] | None = None) -> str:
    """The defaults as the JSON text of the generated file."""
    return json.dumps(web_defaults(thresholds), indent=2) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv[1:]:
        if not DEST.exists() or DEST.read_text(encoding="utf-8") != text:
            sys.exit(f"{DEST.relative_to(ROOT)} is out of date: run python tools/web_defaults.py")
        print(f"{DEST.relative_to(ROOT)} matches config/thresholds.yaml")
    else:
        DEST.write_text(text, encoding="utf-8")
        print(f"wrote {DEST.relative_to(ROOT)}")
