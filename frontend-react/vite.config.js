import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Proxies /api/* to the real FastAPI backend (uvicorn main:app --port 8000)
// so the frontend can just call fetch("/api/...") with no CORS headaches,
// same pattern as the plain HTML/JS frontend already in this project.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
