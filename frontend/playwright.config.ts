import { defineConfig, devices } from "@playwright/test";

/** Requires: backend on :8000 (APP_ENV=development, AI_PROVIDER_ORDER=fake, Auth emulator), Auth emulator on :9099,
 *  frontend with NEXT_PUBLIC_USE_AUTH_EMULATOR=true. Seed data: `cd backend && uv run python -m scripts.dev_seed`. */
export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000", trace: "off", screenshot: "only-on-failure" },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
    { name: "mobile", use: { ...devices["iPhone 14"], browserName: "chromium" } },
  ],
});
