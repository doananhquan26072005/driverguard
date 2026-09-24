# DriverGuard frontend (M6)

React + TypeScript + Vite. Two screens, hash-routed:

| Route | For | Data source |
|---|---|---|
| `#/hud` | Driver, in the car | Edge agent HUD server `http://127.0.0.1:8765` (no login) |
| `#/dashboard` | Fleet manager, engineer, driver | Backend `http://localhost:8100` (login) |

- **HUD**: level L0–L3 with icon + text, reasons, speed / scores, the **"Cảnh báo sai"** button
  (flags the latest alert for 120 s; the edge agent forwards it to the backend), optional
  alert sounds, and a **simulation mode** when no edge agent is running.
- **Dashboard**: event log with filters, fatigue timeline per trip (drowsy_score per minute,
  L1/L2 thresholds, alert markers, table view), thresholds editor (engineer / admin edit,
  manager read-only) next to the false-alarm rate per reason.

## Run

```bash
npm install
cp .env.example .env.local      # optional: other backend / edge URLs
npm run dev                     # http://localhost:5173
```

Needs the backend (`uvicorn backend.app:app --port 8100`) and, for the live HUD, the edge
agent (`python -m edge_agent.main --source 0`). Port 5173 is the origin both of them allow.

```bash
npm test          # vitest (pure helpers)
npm run build     # typecheck + production build in dist/
```
