import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Cross-origin isolation, as backend/static.py serves the built app (M51): the phone detector's wasm
// threads need SharedArrayBuffer, which only an isolated page gets.
const headers = {
  "Cross-Origin-Opener-Policy": "same-origin",
  "Cross-Origin-Embedder-Policy": "require-corp",
};

// Port 5173 is allowed by the backend CORS settings and by the in-car HUD server.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173, strictPort: true, headers },
  preview: { headers },
});
