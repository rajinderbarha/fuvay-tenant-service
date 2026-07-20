import { defineConfig, devices } from "@playwright/test";

/** DESIGN PHASE UX-04B — real headless browser config, first time this
 * workspace has had one. Targets a `next start` server (see package.json
 * "test:browser" script), not `next dev`, so we're testing the same
 * production build verified in tenant-build-report.md. */
export default defineConfig({
  testDir: "./browser-tests",
  timeout: 30000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "browser-test-results.json" }]],
  use: {
    baseURL: "http://localhost:3903",
    trace: "off",
  },
  webServer: {
    command: "npx next start -p 3903",
    url: "http://localhost:3903/dev/ux-04",
    reuseExistingServer: true,
    timeout: 60000,
  },
  projects: [
    { name: "desktop-light", use: { ...devices["Desktop Chrome"], colorScheme: "light", viewport: { width: 1280, height: 800 } } },
    { name: "desktop-dark", use: { ...devices["Desktop Chrome"], colorScheme: "dark", viewport: { width: 1280, height: 800 } } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
