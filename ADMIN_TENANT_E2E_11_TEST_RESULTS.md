# ADMIN-TENANT-E2E-11 — Test Results

## TypeScript
`npx tsc --noEmit` in `frontend/tenant-portal` → **0 errors**, confirmed
after all fixes (`/finance` redirect, `/finance/package` balance rewire,
notification bell fix).

## Build
Not run (`npm run build`) — consistent with established session
practice of using `tsc` as the frontend correctness gate.

## Backend regression
```
pytest tests/ -k "settings or usage_credit or tenant_finance or rbac or cross_app" -q
```
**92 passed, 0 failed.** (One pre-existing static-inspection test,
`test_tenant_finance_ledger_labels_completed_job_deduction`, asserted
label text against the now-redirected `/finance/page.tsx`; fixed to
check the real page, `finance/usage-credit-ledger/page.tsx`, which
already contains the labels — see `tests/test_p0_cross_app_frontend_runtime.py`.)

## Playwright
```
cd frontend/e2e-admin-tenant
E2E_APP=tenant npx playwright test e2e/tenant-finance-notif-settings-e2e11.spec.ts --reporter=list
```
**8 passed, 1 correctly failing (by design).**

```
  ok 1 /finance redirects to the real Package & Credits page, not the legacy wallet page
  ok 2 Usage Credit Balance shows real backend value
  ok 3 Usage Credit Ledger shows real Completed Job Deduction entries with correct arithmetic
  ok 4 Security Deposit page shows real status, separate from usage credits, no withdraw action
  ok 5 Tenant Notifications route loads real data or honest empty state
  ok 6 Tenant notification bell is clickable and navigates to Notifications
  ok 7 Tenant Settings route loads real profile data, tabs work
  x  8 Read-only tenant cannot mutate settings (mutation controls blocked or absent)
     Expected: 403, Received: 200 — "read-only role must not be able to complete a valid tenant-settings mutation"
  ok 9 no mock data / forbidden labels / raw JSON across finance, notifications, settings
```

Test 8 was initially written with a loose assertion
(`expect(res.status()).not.toBe(200)`) that a validation error (`422`,
missing `reason` field) satisfied without proving anything about
permissions. Tightened to send a complete, valid payload and assert the
correct authorization outcome (`403`) — the test now correctly and
strictly fails, proving the RBAC gap with a real, repeatable, automated
assertion rather than a one-off manual curl check. This failing test is
intentionally left in the suite as a permanent regression guard for when
the tenant read-only role tier is eventually implemented.

## Verdict
TypeScript clean, backend clean, Playwright 8/9 green with the 9th
correctly and honestly red — accurately reflecting this sprint's one
real blocker, with a real automated test now guarding it going forward.
