# DriverGuard frontend (M6)

React + TypeScript + Vite. Two screens, hash-routed:

| Route | For | Data source |
|---|---|---|
| `#/hud` | Driver, in the car | Edge agent HUD server `http://127.0.0.1:8765` (no login) |
| `#/hud-preview` | Design review | Fixed scenarios, `?s=l0\|l1\|l1t\|l2o\|l2p\|l2f\|l3\|cam\|down&night=0` |
| `#/dashboard` | Fleet manager, engineer, driver | Backend `http://localhost:8100` (login) |

- **HUD** (`src/hud/`): built to be read in a 0.5 s glance. One large status stage takes the
  level colour, an icon for the reason and an action sentence ("Nhìn về phía trước"); the
  higher the level, the less is on screen (L3: full red screen pulsing at 1 Hz, stop message
  and eyes-closed seconds only). Speed / scores, the **"Cảnh báo sai"** button (latest alert,
  within `hud.feedback_window_s`; the edge agent forwards it to the backend), a sound per kind
  of alert (`chime.ts`) and a **simulation mode** when no edge agent is running.
  `HudScreen` polls the edge agent and plays sounds; `HudView` only renders props.
- **Dashboard**: event log with filters, fatigue timeline per trip (drowsy_score per minute,
  L1/L2 thresholds, alert markers, table view), thresholds editor (engineer / admin edit,
  manager read-only) next to the false-alarm rate per reason.

## Styling

- **Dashboard**: plain CSS in `src/styles.css` (dark tokens of the Version 4 redesign; `.glass` / `.glass-tint` cards, M57).
- **HUD**: Tailwind CSS v4 with the design tokens in `src/index.css` (`@theme`: `hud-*` colours,
  type scale in px, 8 pt spacing, radii, motion), Lucide icons, Inter self-hosted (`@fontsource/inter`, Vietnamese subset; M57)
  (the car may be offline).
- Tailwind runs **without preflight** and scans **only `src/hud/`**, and `styles.css` sits in a
  lower cascade layer (`legacy`), so the dashboard renders exactly as before. Do not name a
  `styles.css` class like a Tailwind utility the HUD uses (`grid`, `inline`, `hidden`, ...): the
  utility would win on dashboard elements too.
- Buttons have no preflight reset: add `border-0` to HUD buttons.

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
