# ADMIN_TENANT_E2E_01 — Browser Tooling Report

## Decision
ONE shared Playwright setup at `frontend/e2e-admin-tenant/` drives BOTH apps via `E2E_APP` env var
(`admin` -> baseURL :3000, webServer runs `frontend/super-admin`; `tenant` -> baseURL :3001, webServer
runs `frontend/tenant-portal`). Chosen over two separate configs because the spec files, helpers, and
route-smoke loop logic are identical between apps; only baseURL/routes/webServer differ, and both are
parameterized. This keeps one source of truth and avoids duplicating helper code.

## Files created
- `frontend/e2e-admin-tenant/playwright.config.ts`
- `frontend/e2e-admin-tenant/e2e/admin-tenant-foundation.spec.ts`
- `frontend/e2e-admin-tenant/e2e/helpers/auth.ts`
- `frontend/e2e-admin-tenant/e2e/helpers/admin-auth.ts`
- `frontend/e2e-admin-tenant/e2e/helpers/tenant-auth.ts`
- `frontend/e2e-admin-tenant/e2e/helpers/seed.ts`
- `frontend/e2e-admin-tenant/e2e/helpers/api.ts`
- `frontend/e2e-admin-tenant/package.json`

## Chrome channel
`playwright.config.ts` uses `{ name: 'chrome', use: { ...devices['Desktop Chrome'], channel: 'chrome' } }`,
cloned verbatim from `frontend/customer-app/playwright.config.ts`. Bundled Chromium download is broken in
this sandbox (TLS decryption error, confirmed in the prior customer-app sprint) — this config never
attempts to use it.

## Dependency resolution
`node_modules` for `frontend/e2e-admin-tenant` is a symlink (`mklink /D`) to
`frontend/customer-app/node_modules`, which already has `@playwright/test` and system Chrome wired up.
No new npm install / network fetch was required.

## Verification
Ran both suites end-to-end against the real dev servers and real backend:
- `E2E_APP=admin npx playwright test --project=chrome` → 7 passed, 11 skipped (tenant-only tests)
- `E2E_APP=tenant npx playwright test --project=chrome` → 11 passed, 7 skipped (admin-only tests)

Total: 18/18 non-skipped tests passing across both apps. Evidence (screenshots, request logs, route-smoke
logs) written to `frontend/e2e-admin-tenant/evidence/`.

## Result
WORKING — foundation tooling proven for both admin and tenant apps using real system Chrome, real dev
servers, real backend, real DB.
