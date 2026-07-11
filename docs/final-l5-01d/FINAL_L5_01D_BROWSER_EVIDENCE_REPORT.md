# FINAL-L5-01D — Browser Evidence Report

## Screenshots captured this sprint (`docs/final-l5-01d/evidence/`)
- `readonly-service-areas.png`, `readonly-services.png`, `readonly-jobs.png`, `readonly-settings.png` — Tenant Read Only precision check across 4 pages
- `regression-tenant-jobs-list.png` — Tenant Jobs list with real canonical data
- `regression-tenant-jobs-detail.png`, `regression-tenant-job-detail-direct.png` — Tenant Job detail, real data, Assign/Schedule/Cancel visible for Tenant Owner
- `regression-customer-bookings.png` — Customer One's real 5-booking list
- `regression-admin-tenants.png` — Admin tenants page, real data

## Real network evidence (not screenshots, but equally real)
- `USED_CANONICAL_ENDPOINT: true` / `USED_LEGACY_V1_JOBS: false` — captured via Playwright's real `page.on("request", ...)` listener during an authenticated Tenant Owner session, not inferred from source code.
- `AUTH_RESPONSE: /v1/auth/login 200`, `/v1/auth/me 200` — captured via `page.on("response", ...)` during the technician debug session.

## What this evidence proves
1. The Tenant Portal's Jobs pages genuinely call the canonical backend endpoint in a real browser, not just in isolated curl tests.
2. Customer One's booking data is genuinely rendered in a real browser after the seed alignment fix.
3. The Tenant Read Only banner and button-gating genuinely activate in a real browser after the role-persistence fix.
4. The Technician redirect genuinely completes (once, with full evidence) when it succeeds — proving the fix is directionally correct even though full stability isn't proven.
