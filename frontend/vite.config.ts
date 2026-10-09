import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Cross-origin isolation, as backend/static.py serves the built app (M51): the phone detector's wasm
// threads need SharedArrayBuffer, which only an isolated page gets.
const isolation = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
};
// The Content-Security-Policy of backend/static.py (M99), word for word (tests/test_backend/test_static.py
// compares the two). On the built app only: the dev server injects inline scripts and a websocket.
const CSP =
  "default-src 'self'; script-src 'self' 'wasm-unsafe-eval'; worker-src 'self' blob:; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; media-src 'self' blob: mediastream:; connect-src 'self' http://127.0.0.1:* http://localhost:*; object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";

// Port 5173 is allowed by the backend CORS settings and by the in-car HUD server.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true, headers: isolation },
  preview: { headers: { ...isolation, "Content-Security-Policy": CSP } },
  // The phone detector's worker imports one of two ONNX Runtime builds once it knows which (M67):
  // only an ES module worker can be split into chunks.
  worker: { format: "es" },
});
