import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Port 5173 is allowed by the backend CORS settings and by the in-car HUD server.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});
