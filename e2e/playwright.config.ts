/**
 * Playwright E2E Configuration — ServiceOS
 * Two projects: super-admin (port 3000) and tenant-portal (port 3001).
 * All API calls mocked at the network layer — no real backend required.
 * Run: npx playwright test
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir:   "./",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries:    process.env.CI ? 2 : 0,
  workers:    process.env.CI ? 1 : undefined,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],

  use: {
    trace:      "on-first-retry",
    screenshot: "only-on-failure",
    video:      "retain-on-failure",
  },

  projects: [
    {
      name:    "super-admin-chromium",
      testDir: "./super-admin",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.SUPER_ADMIN_URL ?? "http://localhost:3000",
        storageState: undefined,
      },
    },
    {
      name:    "tenant-portal-chromium",
      testDir: "./tenant-portal",
      use: {
        ...devices["Desktop Chrome"],
        baseURL: process.env.TENANT_PORTAL_URL ?? "http://localhost:3001",
        storageState: undefined,
      },
    },
    {
      name:    "super-admin-mobile",
      testDir: "./super-admin",
      use: {
        ...devices["iPhone 14"],
        baseURL: process.env.SUPER_ADMIN_URL ?? "http://localhost:3000",
      },
    },
    {
      name:    "tenant-portal-mobile",
      testDir: "./tenant-portal",
      use: {
        ...devices["iPhone 14"],
        baseURL: process.env.TENANT_PORTAL_URL ?? "http://localhost:3001",
      },
    },
  ],

  // Spin up Next.js dev servers before running
  webServer: [
    {
      command: "npm run dev -- --port 3000",
      url:     "http://localhost:3000",
      cwd:     "../frontend/super-admin",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --port 3001",
      url:     "http://localhost:3001",
      cwd:     "../frontend/tenant-portal",
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
});
