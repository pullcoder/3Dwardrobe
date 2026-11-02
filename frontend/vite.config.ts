import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    {
      name: "private-pose-worker",
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url?.split("?")[0] === "/pose-worker.js")
            res.setHeader(
              "Content-Security-Policy",
              "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self';",
            );
          next();
        });
      },
      configurePreviewServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url?.split("?")[0] === "/pose-worker.js")
            res.setHeader(
              "Content-Security-Policy",
              "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; connect-src 'self';",
            );
          next();
        });
      },
    },
  ],
  server: { host: "127.0.0.1", port: 5173, strictPort: true },
  preview: { host: "127.0.0.1" },
});
