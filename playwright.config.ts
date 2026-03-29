import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/specs",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: process.env.CI ? "html" : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    // E2E_API_BASE_URL: Backend API base URL for direct API calls in tests.
    // Defaults to "http://localhost:8000". When using Docker Compose E2E profile,
    // backend-e2e is mapped to port 8001 (e.g. E2E_API_BASE_URL=http://localhost:8001).
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "setup",
      testMatch: /global\.setup\.ts/,
    },
    {
      name: "chromium",
      use: {
        browserName: "chromium",
        storageState: "e2e/.auth/admin.json",
      },
      dependencies: ["setup"],
    },
  ],
  globalSetup: undefined,
});
