import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { fileURLToPath, URL } from "node:url";
import fs from "node:fs";

const proxyTarget = process.env.VITE_PROXY_TARGET || "http://localhost:8080";
const base = process.env.VITE_BASE || "/";

export default defineConfig({
  plugins: [react()],
  base,
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: proxyTarget,
        changeOrigin: true,
        secure: false,
      },
      "/ws": {
        target: proxyTarget,
        ws: true,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: (() => {
        const inputs: Record<string, string> = {
          main: fileURLToPath(new URL("./index.html", import.meta.url)),
        };
        // Only include landing if it exists (for GitHub Pages builds)
        // Docker builds exclude it via .dockerignore
        const landingPath = fileURLToPath(new URL("./landing.html", import.meta.url));
        if (fs.existsSync(landingPath)) {
          inputs.landing = landingPath;
        }
        return inputs;
      })(),
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./", import.meta.url)),
    },
  },
});
