# UX-07 Round 1 Implementation Summary

## Status: UX07_INTEGRATION_PARTIAL

Round 1 of a phase expected to require multiple rounds (per the brief's own
framing, matching UX-05's 7 rounds and UX-06's 6 rounds + 2 backend-fix
cycles). This round prioritized establishing the cross-app proof skeleton,
per the brief's explicit Round-1 priority order.

## What was done (real, verified)

1. **Baseline verification**: confirmed HEAD (`cb2ede0` at session start) is
   a real descendant of all 3 required prior UX baselines
   (7488335/493a132/b426e08) via `git merge-base --is-ancestor`.
2. **Application inventory** (Workstream 1): real route lists for all 4 apps
   captured via `find`/directory listing — see `app-route-inventory.csv`,
   `production-screen-inventory.csv`.
3. **Role entry/routing** (Workstream 2): real login verified live for
   customer, tenant_owner, technician (3 of the required 4 — super_admin
   deferred, no known credential). See `role-navigation-matrix.csv`.
4. **Live E2E proof** (Workstream 19 — the phase's most important
   deliverable): a real, new `ServiceBooking`/`ServiceJob` was created as
   the real seeded customer, seen by the real tenant-portal endpoint,
   assigned to a real technician, seen by the real staff-app endpoint, and
   transitioned (assigned -> accepted) with the transition visible on
   refresh in both tenant-portal and customer-app. Every real ID captured
   in `real-record-evidence.csv`. Full narrative in `live-e2e-evidence.md`.
5. **Cross-app state sync** (Workstream 9): folded into the E2E proof above
   (refresh-then-reverify steps included).
6. **API contract audit** (Workstream 17): documented for the exact
   endpoints exercised in step 4 — see `api-contract-audit.csv`. One real,
   previously-undocumented gap found: `offering_type_id` is functionally
   required for `match-and-price` to succeed for `ac_repair`, but is not
   listed in the draft's own `required_fields` response.
7. **SmartBot language narrowing** (Workstream 12, done ahead of schedule
   since it was small and explicitly named): UX-06's 14-language chat
   registry narrowed to exactly English/हिन्दी/ਪੰਜਾਬੀ per this phase's
   explicit requirement. See `smartbot-language-verification.md`.
8. **Non-change audit** (Workstream 21): `git status`/`git diff --stat`
   confirm only new doc files + the one intentional `chatLanguages.ts`
   narrowing were changed — zero backend files, zero other-app files
   touched. See `backend-non-change-report.md`.

## What was NOT reached this round (deferred, honest)

Workstreams 3, 4, 5 (re-verify only), 6 (partially covered by #4 above), 7,
8, 10, 11, 13, 14, 15, 16, 18 (expanded), 20 (expanded). See
`known-limitations.md` and `deferred-enhancements.md` for itemized reasons.
No WSL app installs, no Playwright browser sessions, no Expo/Next.js dev
servers were started this round — all live-proof work was done via direct
curl against the real running backend, which was judged the highest-value
use of this round's time budget (proving genuine cross-app data continuity)
over re-proving individual apps' own UI wiring, which prior UX phases
already established.

## Final commit (Round 1)

See `final-status-rationale.md` and commit `0f35afa`.

## Round 2 (this update)

Status: `UX07_INTEGRATION_PARTIAL` (see `round-2-status-rationale.md`).

1. **Baseline revalidated**: HEAD `0f35afa`, ancestry, Round 1 booking
   (`BK-20260721-000008`, still `accepted`), and `chatLanguages.ts`'s
   narrowing all re-confirmed intact before any new work.
2. **WSL install + typecheck + test baseline established** for all 4
   relevant app groups (customer-app, staff-app, tenant-portal,
   super-admin) — real results in `typecheck-build-test-baseline.md`.
   Surfaced and fixed 1 real dependency-declaration defect
   (`@testing-library/dom` missing from tenant-portal's `package.json`)
   and precisely diagnosed 1 more (a React version-pin mismatch between
   tenant-portal and super-admin), deliberately left unfixed with full
   reasoning.
3. **Super Admin access resolved**: `SUPER_ADMIN_ACCESS_VERIFIED` using
   `admin@serviceos.local` from the repo's own `scripts/seed_demo_users.py`
   — see `super-admin-access-investigation.md`.
4. **Role-boundary verification** done via real API calls: customer/
   tenant_owner/technician all correctly rejected (`403`) from
   `/v1/admin/*`; 1 real backend authorization defect found (`500` instead
   of `403` for a customer token on a provider-scoped endpoint); 1
   ambiguous finding disclosed, not resolved.
5. **Tenant onboarding**: real route/endpoint source map produced; a real
   live snapshot of the demo tenant's onboarding-status/package-summary
   taken and honestly interpreted (inconsistent with its real operational
   state, most likely due to direct seeding rather than the real
   registration pipeline — not confirmed as a live bug).
6. **Catalog/pricing continuity**: both the standard-price (`ac_repair`)
   and bargain-enabled (`ac_installation`) paths reconfirmed live this
   round with real IDs, cross-referenced in `catalog-entity-continuity.csv`
   and `pricing-continuity.md`.
7. **offering_type_id defect fully root-caused**: `master_services.
   is_type_required = False` for `ac_repair` despite its pricing rules
   being 100% type-scoped — a real catalog-data inconsistency. Full
   investigation in `offering-type-contract-defect.md`; ready backend
   ticket in `backend-remediation-ticket-offering-type.md`; NOT
   implemented (out of scope).
8. **Non-change audit**: exactly 1 code file changed
   (`frontend/tenant-portal/package.json`, 1 line) — zero backend files,
   zero other-app files. See `backend-non-change-report.md`.

## Final commit (Round 2)

See `round-2-status-rationale.md` and commit `c182e7a`.

## Round 3 (this update)

Status: `UX07_INTEGRATION_PARTIAL` (see `round-3-status-rationale.md`).

1. **Full real status-transition graph walked to `completed`**: the
   Round 1 job (`accepted`) was carried through 7 more real, legal
   transitions (`on_the_way -> reached_site -> inspection_started ->
   inspection_done -> service_started -> work_done -> completed`), each
   cross-verified in tenant-portal's execution timeline and the customer
   app's booking detail. See `status-transition-verification.md`.
2. **Quote/checklist/parts audited from real source**: confirmed (not
   assumed) that checklist and quote have zero real backend wiring
   (fixture-only, per the code's own honest comments), and that the
   technician side of the real, backend-supported parts-request lifecycle
   has no client call anywhere in `mobile/staff-app`. See
   `quote-checklist-parts-live-evidence.md`.
3. **Completion, commission and review all verified live**: real
   server-computed commission/credit deduction (`-21.0` against a `775.0`
   job, full ledger audit trail), no fake online payment at any point, and
   a genuinely NEW finding — a real `POST /v1/customer/reviews` endpoint
   (not present/found in UX-06's audit) was discovered and successfully
   used to submit a real review (`REV-56700400`), visible to the tenant.
   One new real backend defect found (500 instead of 422 on malformed
   submissions). See `completion-commission-review-verification.md`.
4. **Super-admin test infrastructure wired**: added the missing
   `vitest`/`@testing-library` devDependencies, a `vitest.config.ts`
   (mirroring tenant-portal's own working config), and a real `test`
   script. Result: 10/13 tests now pass (up from 0 runnable), stable
   across 2 repeated runs.
5. **React version-pin mismatch: genuinely attempted, reverted with firm
   reasoning**: a root `overrides` pin was tried, successfully deduplicated
   react/react-dom, but broke a different dependency's resolution
   (`design-system`'s `lucide-react`), regressing from 3 to 5 failing test
   suites. Reverted; net change to root `package.json` is zero. See
   `react-version-pin-investigation.md`.
6. **Responsive/dark-mode spot-check**: code-level (not screenshot-based)
   check of 4 real production screens across all 4 apps — confirmed
   customer-app has no dark mode (standing gap), the other 3 apps/screens
   do. See `responsive-dark-mode-spotcheck.md`.
7. **All 4 apps' test suites re-run twice this round**: customer-app
   48/48 x2, staff-app 56/56 x2, tenant-portal 42/53 x2 (13/16 suites),
   super-admin 10/13 x2 (3/4 suites) — all stable, no flakiness.
8. **Non-change audit**: net code changes this round are
   `frontend/super-admin/package.json` (modified) +
   `frontend/super-admin/vitest.config.ts` + `test-setup.ts` (new) — root
   `package.json`'s temporary override was fully reverted (zero net diff).
   Zero backend files touched.

## Final commit (Round 3)

See `round-3-status-rationale.md` and the commit hash reported at the end
of this round's session.
