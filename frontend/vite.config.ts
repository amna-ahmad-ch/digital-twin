import { defineConfig } from "vite";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  build: {
    rollupOptions: {
      input: {
        main: resolve(root, "index.html"),
        admin: resolve(root, "admin/index.html"),
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/admin/login": "http://127.0.0.1:8000",
      "/admin/logout": "http://127.0.0.1:8000",
      "/admin/api": "http://127.0.0.1:8000",
    },
  },
});
