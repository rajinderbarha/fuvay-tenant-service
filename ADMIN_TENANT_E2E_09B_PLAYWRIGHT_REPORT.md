# ADMIN-TENANT-E2E-09B — Playwright Report

Command: `E2E_APP=tenant npx playwright test e2e/tenant-rbac-bookability-e2e09b.spec.ts
e2e/tenant-service-setup-e2e09.spec.ts --project=chrome --reporter=list`
(real system Chrome, `channel: 'chrome'`, against live backend :8000 + tenant-portal :3001)

```
Running 14 tests using 1 worker

  ok  1 API: read-only blocked 403 on pricing, types, publish, save-draft, coverage (1.8s)
  ok  2 API: unauthenticated -> 401 (45ms)
  ok  3 API: Owner mutation succeeds and is reverted; Manager mutation succeeds, real validation still runs (1.3s)
  ok  4 Browser: read-only login sees setup wizard read-only banner + disabled Save/Publish (6.4s)
  ok  5 Browser: owner login sees setup wizard without read-only banner (5.7s)
  ok  6 API: live bookability status uses tenant_billing (is_bookable true) (430ms)
  ok  7 API: live match-and-price returns Demo AC Services with real Low/Mid/High options (1.0s)
  ok  8 route smoke: setup/services, provider/service-coverage, legacy redirect, onboarding-status, dashboard (27.4s)
  ok  9 tenant name "Demo AC Services" appears on dashboard and setup pages (10.7s)
  ok 10 service coverage page: coverage matrix, Ludhiana/141001 area visible (8.3s)
  ok 11 type-specific brand pricing: Split AC+LG and Window AC+LG differ (1.8s)
  ok 12 provider price range: invalid range rejected (666ms)
  ok 13 E2E-09B FIXED: read-only tenant user is blocked by access_scope at 403 (759ms)
  ok 14 mutation UI hidden or gated for read-only login on service coverage page (21.5s)

  14 passed (1.7m)
```

New spec: `frontend/e2e-admin-tenant/e2e/tenant-rbac-bookability-e2e09b.spec.ts` (7 tests).
Modified spec: `frontend/e2e-admin-tenant/e2e/tenant-service-setup-e2e09.spec.ts` — the
previously-documented "KNOWN GAP" test (#13 above) is now flipped to assert 403, and it
passes for real against the fixed backend.

No NaN/undefined/raw JSON assertions failed; no forbidden labels found in any page body
checked; `tenant_wallets` string confirmed absent from the real match-and-price response body.
Evidence screenshots + logs at `frontend/e2e-admin-tenant/evidence/e2e09b/`.
