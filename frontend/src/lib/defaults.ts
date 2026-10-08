// Numbers of config/thresholds.yaml for the time a page has no agent to hand them over: before the
// first HUD state, in the scripted demo, on the dashboard and the driving controls. While a trip runs
// the agent's own numbers win (HudSnapshot.display, WebAgent.settings()): they include what engineers
// tuned on the dashboard. The JSON is written by tools/web_defaults.py and checked against the YAML
// by tests/test_edge_agent/test_m85_no_hardcode.py; no page keeps a threshold of its own.
import GEN from "./defaults.gen.json";
import type { HudDisplay } from "./types";

export const DEFAULTS = GEN;
export const HUD_DEFAULTS: HudDisplay = GEN.hud;
