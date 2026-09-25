import { useEffect, useState } from "react";
import Dashboard from "./dashboard/Dashboard";
import HudPreview from "./hud/HudPreview";
import HudScreen from "./hud/HudScreen";

// Hash routes: #/hud (in-car screen, no login), #/hud-preview (every HUD state, for design review)
// and #/dashboard (fleet manager / engineer / driver).
function route(): "hud" | "hud-preview" | "dashboard" {
  const hash = window.location.hash;
  if (hash.startsWith("#/hud-preview")) return "hud-preview";
  return hash.startsWith("#/hud") ? "hud" : "dashboard";
}

export default function App() {
  const [page, setPage] = useState(route);
  useEffect(() => {
    const onHash = () => setPage(route());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  if (page === "hud-preview") return <HudPreview />;
  return page === "hud" ? <HudScreen /> : <Dashboard />;
}
