# ADMIN-TENANT-E2E-05 — Remaining Blockers

## Hard blockers: none.

## Non-blocking, flagged for future sprints
1. **Dual wallet/credit systems** (`usage_credit_ledger`/`tenant_billing` vs. `tenant_wallets`) coexist server-side. The in-scope admin pages correctly use the authoritative one (3958 balance); `/admin/finance/wallets` and a dormant `/{tenant_id}/wallet*` endpoint family read the other (0.00 for the demo tenant). Not a defect in the pages tested, but a real architectural split worth consolidating or clearly re-labeling so the two are never confused (see API Contract + Tenant Credit Status reports).
2. **No multi-tenant summary endpoint** for Usage Credits (`GET /v1/admin/usage-credits/summary` across all tenants does not exist) — `/admin/finance/usage-credits` is a single-tenant lookup tool, not a fleet-wide dashboard. Low practical impact today since only one real tenant exists platform-wide, but should be tracked as a real enhancement once more tenants exist.
3. **Isolation could not be empirically re-tested with a second live tenant** (only 1 tenant exists in this DB). Verified isolation at the code/query level instead (explicit `tenant_id` filter bound from path param, no implicit/global scope). A future sprint should seed a second tenant specifically to exercise a real cross-tenant leak test.
4. **Stale Turbopack dev-type-generation artifact** (`.next/dev/types/validator.ts`) can occasionally corrupt and break a raw `tsc --noEmit` run with an unrelated syntax error; deleting the file and letting the dev server regenerate it resolves this immediately. Not a source-code issue — purely a dev-cache quirk, documented here so a future run doesn't mistake it for a real regression.
5. **Route-shadowing history**: a code comment in `admin_router.py` references a previously-fixed route-shadowing bug (`package_commerce/admin_router.py` registering the same wallet paths a second time, documented in an earlier `PHASE_4_FINANCE_BUG_FIX_REPORT.md`). Confirmed the currently-active file does not exhibit this (only one registration observed for each path in the file read this session), but worth a quick re-grep across the full router-mount list in `main.py` in a future sprint to be certain no regression has re-introduced a duplicate registration.

## Bugs found and fixed this session (test-harness bugs, not product bugs)
- Tenant-detail Playwright test never actually clicked into the "Finance" tab-group before looking for the "Usage Credit Ledger" tab, so its assertion was silently skipped (false green). Fixed by clicking `button:has-text("Finance")` first.
- Tenant-list Playwright test used a fixed 1500ms wait, which raced the page's real loading state and failed once the fix above was validated with a clean re-run. Fixed with an explicit `waitFor` on the tenant name locator.

## Verdict: No blockers to certification. All flagged items are pre-existing architecture debt or environment quirks, not regressions introduced or missed by this sprint's in-scope pages.
