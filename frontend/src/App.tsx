import { useEffect, useState } from "react";
import Dashboard from "./dashboard/Dashboard";
import HudScreen from "./hud/HudScreen";

// Hash routes: #/hud (in-car screen, no login) and #/dashboard (fleet manager / engineer / driver).
function route(): "hud" | "dashboard" {
  return window.location.hash.startsWith("#/hud") ? "hud" : "dashboard";
}

export default function App() {
  const [page, setPage] = useState(route);
  useEffect(() => {
    const onHash = () => setPage(route());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  return page === "hud" ? <HudScreen /> : <Dashboard />;
}
