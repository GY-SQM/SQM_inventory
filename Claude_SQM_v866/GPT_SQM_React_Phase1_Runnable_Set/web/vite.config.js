import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// SQM React 1단계:
// - 프론트: Vite dev server(5173)
// - 백엔드: FastAPI(8000)
// - /api 요청은 FastAPI로 프록시
export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
