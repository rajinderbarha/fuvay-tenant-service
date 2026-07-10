# ADMIN-TENANT-E2E-05 — Usage Credit Ledger Report

Ledger surfaces in two places, both backed by the same authoritative table/endpoint:
1. `/admin/finance/usage-credits` (single-tenant lookup tool) — `GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger`.
2. `/admin/tenants/{id}` → Finance tab-group → "Usage Credit Ledger" sub-tab (internal id `wallet`) — same endpoint, via `usageCreditsAdminApi.getTenantLedger(id)` (see `app/admin/tenants/[id]/page.tsx` lines 1062-1067).

## Real ledger rows (Demo AC Services, verified via psql)
Two rows, both `event_type=completed_job_deduction`, `credit_delta=-21.00`:
- balance_before=4000.00 → balance_after=3979.00 (job 6628eb52…, created 2026-07-09 19:50:12)
- balance_before=3979.00 → balance_after=3958.00 (job 34fc415e…, created 2026-07-09 22:55:57)

## Cross-surface consistency (real bug found + fixed this session)
Before this session's fix, the tenant-detail "Usage Credit Ledger" tab called `commerceApi.walletBalance(id)`, which reads a **different, disconnected table** (`tenant_wallets`, balance 0.00 for this tenant) — meaning the tab showed 0 while `/admin/finance/usage-credits` showed 3958 for the same tenant. This was already corrected in a prior pass of this sprint (see code comment at `app/admin/tenants/[id]/page.tsx:1062-1067`): the tab now calls `usageCreditsAdminApi.getTenantLedger(id)`, the same authoritative source.

## Playwright verification (this session, fresh run)
The existing spec's tenant-detail test had a **second real bug**: it looked for the "Usage Credit Ledger" tab via a plain text locator without first clicking the "Finance" tab-group pill. Because `TABS` are filtered by `groupForTab(tab).tabs.includes(tb.id)` and the page defaults to the "Overview" group, the Finance sub-tab (including "Usage Credit Ledger") never renders in the DOM until the Finance group is selected — the test was silently taking its `else` branch and not actually verifying the ledger tab content.

Fixed in `frontend/e2e-admin-tenant/e2e/admin-finance-tenant-e2e05.spec.ts` (test `tenant detail (Tenant 360)`): now clicks `button:has-text("Finance")` before locating the ledger tab. Re-ran: evidence log confirms
```
Contains Demo AC Services: true
Ledger tab contains 3958 (matches Usage Credits page): true
```
Screenshot: `frontend/e2e-admin-tenant/evidence/e2e05/tenant-detail-ledger.png`.

## Verdict: PASS. Ledger data real, arithmetic verified, both surfaces now genuinely consistent (3958 in both places), confirmed via a real (fixed) browser test, not just a code read.
