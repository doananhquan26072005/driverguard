import { useEffect, useState } from "react";
import Dashboard from "./dashboard/Dashboard";
import DriveScreen from "./drive/DriveScreen";
import HudPreview from "./hud/HudPreview";
import HudScreen from "./hud/HudScreen";
import LiveScreen from "./live/LiveScreen";

// Hash routes: #/hud (in-car screen, no login), #/hud-preview (every HUD state, for design review)
// #/live (the whole agent in this browser, on the visitor's camera), #/drive (web driving controls
// for a #/live session, M31) and #/dashboard (fleet manager / engineer / driver).
function route(): "hud" | "hud-preview" | "live" | "drive" | "dashboard" {
  const hash = window.location.hash;
  if (hash.startsWith("#/hud-preview")) return "hud-preview";
  if (hash.startsWith("#/drive")) return "drive";
  if (hash.startsWith("#/live")) return "live";
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
  if (page === "live") return <LiveScreen />;
  if (page === "drive") return <DriveScreen />;
  return page === "hud" ? <HudScreen /> : <Dashboard />;
}
