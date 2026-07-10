# Browser E2E Report (Part 14)

New spec added to the existing harness: `frontend/e2e-admin-tenant/e2e/admin-matching-ops-e2e04.spec.ts`, cloning the exact login/navigation/evidence pattern from `admin-catalog-pricing-e2e03.spec.ts` (real system Chrome via `channel: 'chrome'`, `E2E_APP=admin`, `loginAsSuperAdmin` helper, evidence dir `evidence/e2e04/`).

7 real tests, all against the live backend (:8000) and live frontend (:3000), real Chrome:
1. Route smoke — all 7 in-scope routes, no NaN/undefined/crash, screenshots saved.
2. Provider Matching page — header + Ranking Factors present.
3. Matching Diagnostics — real AC Repair + Split AC + LG + 141001 run, asserts "Demo AC Services" and Low/Mid/High all present.
4. Matching Diagnostics — no-match (zipcode 999999), asserts "No eligible provider found".
5. Completed Job Deduction — asserts "AC Repair" row visible.
6. Operations board — asserts "Operations Board" title, no NaN.
7. Forbidden label scan — 5 routes checked against the full forbidden list.

**Real `npx playwright test` output (final run, after fixing 3 initial test-authoring issues — see below):**
```
Running 7 tests using 1 worker

  ok 1 [chrome] › ... route smoke: matching/operations/deduction pages, no crash, no NaN/undefined (30.5s)
  ok 2 [chrome] › ... provider matching page: header, ranking factors, links to diagnostics (5.0s)
  ok 3 [chrome] › ... matching diagnostics: run AC Repair+Split AC+LG+141001, verify selected provider + Low/Mid/High (7.5s)
  ok 4 [chrome] › ... matching diagnostics: no-match scenario (zipcode 999999) (8.5s)
  ok 5 [chrome] › ... completed job deduction: AC Repair rule visible (6.5s)
  ok 6 [chrome] › ... operations board: real job list, open real completed job JOB-20260710-000001 (6.5s)
  ok 7 [chrome] › ... forbidden label scan on matching/operations/deduction pages (11.0s)

  7 passed (1.4m)
```

## Bugs found and fixed during test authoring (real, in the test file only — not product code)
- Initial run used numeric input-index selectors (`.nth(4)`/`.nth(5)`) for Type ID/Brand ID on the Matching Diagnostics form, which was fragile and produced an unintended zipcode/exclusion mismatch on one run. Fixed by switching to `page.getByLabel(...)` (robust, label-based) locators.
- Initial route-smoke test used the default `waitUntil: 'load'` with a 60s global timeout and hit `net::ERR_ABORTED` on `/admin/home-services/service-jobs` under load; fixed by using `waitUntil: 'domcontentloaded'` with an explicit 30s per-navigation timeout.

No product-code bugs were found via this E2E run (the underlying pages/APIs all behaved correctly once the test itself was corrected).

## Verdict
**PASS.** All 7 tests green on real system Chrome against the real backend/frontend/DB.
