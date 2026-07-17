import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/health": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/speedtest": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/history": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/dashboard": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/statistics": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/isp": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/recommendation": { target: "http://127.0.0.1:8000", changeOrigin: true },
    },
  },
});
