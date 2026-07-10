# ADMIN_TENANT_E2E_01 — Test Results

## TypeScript (`npx tsc --noEmit`)
- `frontend/super-admin`: **0 errors**
- `frontend/tenant-portal`: **0 errors**

## Build (`npm run build`)
- `frontend/super-admin`: **succeeded**, full route manifest printed (all `/admin/*` routes present,
  static + dynamic as expected)
- `frontend/tenant-portal`: **succeeded**, full route manifest printed (all tenant routes present)

## Lint (`npm run lint` → `next lint`)
- Both apps: **fails immediately** with `Invalid project directory provided, no such directory:
  .../lint` — Next.js 16.2.9 removed the `next lint` subcommand/CLI shape this `package.json` script
  relies on. This is a **pre-existing tooling gap** (not introduced by this sprint, not something the
  scope of a foundation E2E sprint should silently "fix" by rewriting the lint pipeline). Documented
  per spec instruction ("if no valid ESLint config exists, document as a pre-existing tooling gap, do
  not fail the sprint over it alone").

## npm test
- Neither app has a `test` script configured in `package.json` — no unit test runner exists in either
  frontend. Pre-existing, documented.

## Playwright (`frontend/e2e-admin-tenant/e2e/admin-tenant-foundation.spec.ts`)
- `E2E_APP=admin npx playwright test --project=chrome`: **7 passed**, 11 skipped (tenant-only tests)
  - backend seed baseline bookable (real API)
  - super admin browser login → admin dashboard
  - 5x admin route smoke (dashboard, tenants, service-catalog, pricing-rules, finance/usage-credits)
- `E2E_APP=tenant npx playwright test --project=chrome`: **11 passed**, 7 skipped (admin-only tests)
  - tenant owner browser login → dashboard (name assertion)
  - 8x tenant route smoke
  - tenant read-only browser login
  - read-only mutation-attempt probe (documents a real gap, non-destructive to seed data by design)
- **18/18 non-skipped tests passing** across both invocations.

## Backend regression check
- `python -m pytest tests/test_auth_login_fix.py -q` → **16 passed** (confirms the 3 new users created
  via direct SQL insert did not break auth flows).
- Full backend regression suite (thousands of tests across the whole repo, per prior sprints) was NOT
  re-run in full — out of scope for a frontend-focused foundation sprint that touched only 1 frontend
  file (`tenant-portal/app/login/page.tsx`) and 3 new DB rows in a pre-existing table with no schema
  change. Auth-specific tests were run as the most directly relevant regression check.

## Bugs found this sprint
1. Tenant login page mis-read `/v1/tenant/dashboard/runtime` response shape (`rdata.tenant_name` flat
   vs real `rdata.tenant.business_name` nested) → dashboard showed placeholder "Your Business" instead
   of the real tenant name.
2. `PUT /v1/provider/business-profile` has no `access_scope` enforcement — a
   `customer_support_limited` user could mutate the tenant's business profile and trigger
   re-verification.
3. Admin sidebar active-state highlight does not track Home Services sub-routes (stays on
   "Dashboard").
4. Onboarding tour modal intercepts every first page load in both apps, complicating future automated
   page content assertions.
5. `next lint` is broken in both apps under Next.js 16.2.9 (pre-existing tooling gap, not this
   sprint's regression).
6. "Tenant Payouts" (plural) label used in `admin/settings` — a near-miss of the forbidden "Tenant
   Payout" label.

## Bugs fixed
1. Tenant login page tenant-name resolution — fixed in
   `frontend/tenant-portal/app/login/page.tsx` (rdata.tenant?.business_name fallback added). Verified
   via Playwright: tenant dashboard now shows "Demo AC Services".
2. Accidental data corruption caused while investigating bug #2 above (business_name and
   verification_status mutated on the real Demo AC Services tenant) was fully reverted via SQL and
   re-verified end-to-end bookable afterward. The E2E probe test itself was rewritten to be
   non-destructive (reads-before-writes, restores after).

## Bugs NOT fixed (documented as gaps for future sprints)
- #2 (access_scope enforcement gap) — a real backend RBAC hole, needs a dedicated fix + tests in a
  security-focused sprint, out of scope to patch blind in a foundation sprint.
- #3 (sidebar active state) — cosmetic, deferred.
- #4 (onboarding tour blocking automated screenshots) — needs an E2E-friendly dismiss mechanism,
  deferred to the next page-by-page sprint.
- #5 (next lint) — pre-existing tooling/Next-version gap, out of scope.
- #6 (label near-miss) — cosmetic rename, deferred.
