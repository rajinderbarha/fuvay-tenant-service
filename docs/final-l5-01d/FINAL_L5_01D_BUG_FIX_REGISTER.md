# FINAL-L5-01D — Bug Fix Register

## L5-01D-001: Tenant Jobs uses legacy `/v1/jobs`
- **Evidence**: Real browser session showed "No jobs match your filters" despite 5 real canonical jobs existing; `lib/api.ts:245` called `/v1/jobs` (422 `TENANT_REQUIRED` for this call shape).
- **Severity**: High.
- **Root cause**: Frontend wired to the legacy field_ops job system instead of the canonical `service_jobs`-backed endpoint.
- **Fix**: Added `serviceJobsApi` typed module (`/v1/provider/my-records/jobs`); rewrote `app/(tenant)/jobs/page.tsx` and `[id]/page.tsx` to use it + `serviceJobAssignmentApi` for actions.
- **Regression test**: TypeScript clean (0 errors); live curl confirms real data; real browser confirms `USED_CANONICAL_ENDPOINT: true`, `USED_LEGACY_V1_JOBS: false`.
- **Browser evidence**: `regression-tenant-jobs-list.png`, `regression-tenant-jobs-detail.png`.
- **Final status**: **FIXED, verified live and in browser.**

## L5-01D-002: Customer seed/API booking source mismatch
- **Evidence**: `GET /v1/customer/bookings` (canonical, correct endpoint) returned empty because FINAL-L5-01's seed populated `bookings` while the endpoint reads `service_bookings`.
- **Severity**: Medium (data-completeness, not security).
- **Root cause**: `creation_service.py:150` proves `service_jobs.booking_id` must reference `service_bookings.id`, not `bookings.id` — the seed's original choice of table was wrong.
- **Fix**: `canonical_seed_final_l5_01.py::upsert_job()` rewritten to create a `home_service_booking_drafts` row + a `service_bookings` row per job, matching the real application flow exactly. `bookings` table no longer written to by this seed.
- **Regression test**: Idempotency re-proven (100% skips on rerun); SQL join confirms 5/5 correct `service_jobs.booking_id` → `service_bookings.id` links; repeated across a full reset cycle with identical results.
- **Browser evidence**: `regression-customer-bookings.png` — real 5-booking list.
- **Final status**: **FIXED, verified live, in browser, and across a full repeatability cycle.**

## L5-01D-003: Tenant Read Only UI precision inconclusive
- **Evidence**: Real browser test showed inconsistent/missing ReadOnlyBanner across pages in earlier sessions.
- **Severity**: Medium.
- **Root cause**: Two compounding bugs — (a) login handler never persisted user role to `localStorage`; (b) `isReadOnly()` checked for `"tenant_read_only"` (underscore) while the real role is `"tenant_readonly"` (no underscore).
- **Fix**: Added role persistence at login + `getUserRole()` helper; fixed `isReadOnly()`'s string match; wired `ReadOnlyBanner` + button-gating into the two migrated Jobs pages.
- **Regression test**: Real browser re-test across 4 pages — banner now appears consistently on all 4 (was flaky/missing before); 0 enabled mutation buttons on Jobs pages.
- **Browser evidence**: `readonly-service-areas.png`, `readonly-services.png`, `readonly-jobs.png`, `readonly-settings.png`.
- **Final status**: **FIXED for the in-scope Jobs pages, verified live.** One new real finding surfaced by the same fix: Service Areas' "+ Add Zone" button remains ungated — logged as L5-01D-005, not fixed (out of scope).

## L5-01D-004: Technician redirect timing inconclusive
- **Evidence**: Real browser session showed login succeeding (200) but the page not landing on `/staff/dashboard` within a short wait.
- **Severity**: Medium.
- **Root cause**: `window.location.href` full-page reload, compounded by Next.js dev-mode Fast Refresh interference — confirmed via detailed console/network capture showing the transition genuinely completing, just slowly and unreliably-trackably.
- **Fix**: Replaced with `useRouter().push()` — SPA transition, verified 2,756ms in an isolated run.
- **Regression test**: 5-run repeated-login batch — 1/5 succeeded quickly, 4/5 timed out. Account lockout ruled out via direct DB check (`failed_login_attempts=0`).
- **Browser evidence**: Isolated debug capture shows full real success (`FINAL_URL: /staff/dashboard`, real dashboard content).
- **Final status**: **Fix applied and verified correct in isolation; NOT proven stable across repeated runs.** Second contributing factor not fully root-caused (leading candidate: test-harness/dev-server resource contention in this exceptionally long session). **Open item.**

## L5-01D-005: Service Areas "+ Add Zone" button not gated for Tenant Read Only (new finding)
- **Evidence**: Real browser screenshot shows the button visible and enabled for a read-only user.
- **Severity**: Low-medium (backend still blocks the actual mutation — confirmed via the granular `tenant_service_area:create` permission check returning 403 — so this is a UX gap, not a security hole).
- **Root cause**: Not investigated this sprint — Service Areas page is outside the Jobs/Bookings scope this mission defines.
- **Fix**: Not applied.
- **Final status**: **DOCUMENTED, not fixed** — carried to remaining blockers.

## L5-01D-006: Embedded-error pattern instead of HTTP status codes (cross-cutting finding)
- **Evidence**: Cross-customer booking access and missing-booking cases both return `HTTP 200` with `{"success": false, "error": {...}}` rather than `403`/`404`.
- **Severity**: Low (no data leakage, API-consistency issue only).
- **Fix**: Not applied — architectural pattern used consistently across this part of the codebase, not a one-line fix.
- **Final status**: **DOCUMENTED, not fixed.**
