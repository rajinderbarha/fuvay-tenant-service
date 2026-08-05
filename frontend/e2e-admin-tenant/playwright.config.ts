import { defineConfig, devices } from '@playwright/test';

/**
 * Shared Playwright config for Admin (super-admin, port 3000) and
 * Tenant (tenant-portal, port 3001) portals.
 *
 * Both apps are separate Next.js processes, so rather than maintaining two
 * near-identical configs, this ONE config drives both via the E2E_APP env var:
 *   E2E_APP=admin  -> baseURL http://localhost:3000, webServer runs super-admin
 *   E2E_APP=tenant -> baseURL http://localhost:3001, webServer runs tenant-portal
 * Default (no E2E_APP set) is 'admin'. This mirrors the proven pattern from
 * frontend/customer-app/playwright.config.ts (system Chrome via channel:'chrome',
 * bundled Chromium download is broken in this sandbox).
 */
const APP = (process.env.E2E_APP || 'admin') as 'admin' | 'tenant';

const APP_CONFIG = {
  admin: {
    port: 3000,
    cwd: '../super-admin',
  },
  tenant: {
    port: 3001,
    cwd: '../tenant-portal',
  },
}[APP];

export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    baseURL: `http://localhost:${APP_CONFIG.port}`,
    // Full capture (was trace:'retain-on-failure' / screenshot:'only-on-failure').
    // Capturing on PASS too matters here: several bugs found in this codebase
    // were pages that returned 200 and "passed" while rendering fabricated or
    // empty data, which a failure-only trace can never show you.
    trace: 'on',
    screenshot: 'on',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    },
  ],
  webServer: {
    command: 'npm run dev',
    cwd: APP_CONFIG.cwd,
    url: `http://localhost:${APP_CONFIG.port}`,
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
