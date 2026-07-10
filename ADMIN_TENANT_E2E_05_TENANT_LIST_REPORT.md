# ADMIN-TENANT-E2E-05 — Tenant List Report

Route: `/admin/tenants` (`app/admin/tenants/page.tsx`, 1043 lines), backed by `adminTenantsApi`.

## Real elements
- Summary/KPI cards: Total Providers, Active, Pending Review, Pending Setup, Changes Requested, Suspended, Rejected, Package Pending Approval — all live counts (shown as "…" briefly while loading, confirmed by the initial failed test run this session, see Bugs Found).
- Filters: status (10 states incl. Active/Suspended/Archived/Deactivated), verification stage (11 states), plan (Free/Starter/Growth/Professional/Enterprise/Advanced), search box.
- Table row for "Demo AC Services" (the only real platform tenant) renders with status Active.
- Export + Add Tenant actions present in header.

## Bug found and fixed this session
Initial Playwright run of the `tenant list` test used a fixed 1500ms `waitForTimeout` before reading body text; the summary cards were still showing "…" (loading placeholder) at that point and the row for "Demo AC Services" had not yet rendered, causing a real, reproducible test failure (not a flake — same failure on the run that exposed it). Fixed by replacing the fixed timeout with an explicit `page.locator('text=Demo AC Services').first().waitFor({ state: 'visible', timeout: 15000 })` in `frontend/e2e-admin-tenant/e2e/admin-finance-tenant-e2e05.spec.ts`. Re-run: passed, `tenant-list.log` confirms `Contains Demo AC Services: true`, screenshot `evidence/e2e05/tenant-list.png`.

## Verdict: PASS — real data-backed list page, single real tenant renders correctly with correct status; the one bug found was in the test's wait strategy, not the product.
