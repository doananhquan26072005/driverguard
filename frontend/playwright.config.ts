// End-to-end tests of the web app (npm run e2e): the backend on a throwaway database, the frontend
// built for tests (VITE_E2E=1: block 3 reads synthetic landmark numbers instead of MediaPipe, see
// src/live/agent.ts) and Chrome's fake camera. No face image is involved. Pyodide is served by the app
// itself (scripts/web-runtime.mjs, M99), and the build is served with the Content-Security-Policy of
// backend/static.py, so a page that needed another origin or `eval` would fail here.
import { defineConfig } from "@playwright/test";

const API_PORT = 8199;
const WEB_PORT = 5180;
const PYTHON = process.env.PYTHON ?? "python";
const CACHE = "e2e/.cache"; // relative to frontend/, read by the tests too
const DB = `frontend/${CACHE}/e2e.db`;

export default defineConfig({
  testDir: "e2e",
  testMatch: "**/*.e2e.ts", // not *.test.ts: those are vitest's
  timeout: 240_000, // Pyodide + numpy download on a cold browser profile
  expect: { timeout: 20_000 },
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    permissions: ["camera"],
    launchOptions: { args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"] },
    trace: "retain-on-failure",
  },
  webServer: [
    {
      // tools/e2e_setup.py: fresh database with the test accounts, edge_agent.zip, synthetic faces.
      command: `${PYTHON} tools/e2e_setup.py --db ${DB} --faces frontend/${CACHE}/faces.json && ${PYTHON} -m uvicorn backend.app:app --host 127.0.0.1 --port ${API_PORT}`,
      cwd: "..",
      url: `http://127.0.0.1:${API_PORT}/health`,
      env: {
        DG_DB_PATH: DB,
        DG_JWT_SECRET: "e2e-only-secret-not-for-production-0123456789",
        DG_CORS_ORIGINS: `http://localhost:${WEB_PORT}`,
      },
      timeout: 60_000,
    },
    {
      // A production build (not the dev server), with the E2E hook compiled in.
      command: `node scripts/web-runtime.mjs && npx vite build --outDir ${CACHE}/dist --emptyOutDir && npx vite preview --outDir ${CACHE}/dist --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}`,
      env: { VITE_E2E: "1", VITE_API_URL: `http://127.0.0.1:${API_PORT}` },
      timeout: 120_000,
    },
  ],
});
