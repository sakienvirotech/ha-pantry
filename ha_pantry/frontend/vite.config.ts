import preact from "@preact/preset-vite";
import { defineConfig } from "vite";

export default defineConfig({
  // Ingress serves the app under a dynamic path, so asset URLs must be relative.
  base: "./",
  plugins: [preact()],
  server: { proxy: { "/api": "http://127.0.0.1:8099" } },
});
