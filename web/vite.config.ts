/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The dashboard is always served from the root of the loopback server, so
// unlike the explorer there is no need for a path-agnostic base. The proxy
// exists only for `pnpm dev`: in production the Python server serves both the
// API and this bundle from one origin.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8770",
    },
  },
  test: {
    coverage: {
      exclude: ["src/main.tsx", "src/test/**", "src/**/*.d.ts"],
      include: ["src/**/*.{ts,tsx}"],
      provider: "v8",
      thresholds: {
        branches: 100,
        functions: 100,
        lines: 100,
        statements: 100,
      },
    },
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"],
    setupFiles: ["./src/test/setup.ts"],
  },
});
