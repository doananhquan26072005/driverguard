import { useEffect, useState } from "react";
import Dashboard from "./dashboard/Dashboard";
import DriveScreen from "./drive/DriveScreen";
import GuideScreen from "./guide/GuideScreen";
import HudPreview from "./hud/HudPreview";
import HudScreen from "./hud/HudScreen";
import LiveScreen from "./live/LiveScreen";
import PrivacyScreen from "./privacy/PrivacyScreen";

// Hash routes: #/hud (in-car screen, no login), #/hud-preview (every HUD state, for design review)
// #/live (the whole agent in this browser, on the visitor's camera), #/drive (web driving controls
// for a #/live session, M31), #/guide (the guide for a new user, M102), #/privacy (what happens to a
// driver's data, M106; the path /privacy opens it too) and #/dashboard (fleet manager / engineer / driver).
function route(): "hud" | "hud-preview" | "live" | "drive" | "guide" | "privacy" | "dashboard" {
  const hash = window.location.hash;
  if (hash.startsWith("#/privacy") || (!hash && window.location.pathname === "/privacy")) return "privacy";
  if (hash.startsWith("#/hud-preview")) return "hud-preview";
  if (hash.startsWith("#/drive")) return "drive";
  if (hash.startsWith("#/guide")) return "guide";
  if (hash.startsWith("#/live")) return "live";
  if (hash.startsWith("#/hud")) return "hud";
  return hash.startsWith("#/dashboard") ? "dashboard" : "live"; // no address: the first page
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
  if (page === "guide") return <GuideScreen />;
  if (page === "privacy") return <PrivacyScreen />;
  return page === "hud" ? <HudScreen /> : <Dashboard />;
}
