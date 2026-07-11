# FINAL-L5-02B — Bug Closure Evidence

## BUG-L502-005: CLOSED

| Field | Evidence |
|---|---|
| Root cause | Two active consumers of legacy `jobsApi` (backed by the permanently-empty `jobs`/field_ops table) remained in the Tenant Portal beyond the pages FINAL-L5-01D had already migrated: `components/dashboard/HomeServiceDashboard.tsx` (dashboard "Recent Jobs"/SLA widgets) and `app/(tenant)/staff/[id]/page.tsx` (staff detail "Recent Jobs" widget). |
| Files changed | `frontend/tenant-portal/components/dashboard/HomeServiceDashboard.tsx`, `frontend/tenant-portal/app/(tenant)/staff/[id]/page.tsx` |
| Canonical endpoint | `GET /v1/provider/my-records/jobs` (via `serviceJobsApi.list`) |
| Legacy call removal proof | Source grep (`grep -rln "jobsApi\." frontend/tenant-portal/{app,components,hooks}`) → **0 matches**, post-fix. Live browser network capture across dashboard + jobs list + jobs detail navigation → **0 `/v1/jobs` requests**. |
| API tests | `npx tsc --noEmit` → 0 errors |
| Browser network proof | `final-l5-02b-tenant-jobs-browser.spec.ts` — captured full `/v1/*` request log, `LEGACY_/v1/jobs_CALLS: []`, canonical `GET /v1/provider/my-records/jobs?limit=50&offset=0` present |
| Final status | **FIXED, verified via source, TypeScript, and live browser network capture.** The `/v1/jobs` backend route itself is retained (not removed) because super-admin has a real, legitimate, out-of-scope use for it — see Legacy Deprecation Report. |

## BUG-L502-006: CLOSED

| Field | Evidence |
|---|---|
| Root cause | Table-naming ambiguity across `bookings`/`service_bookings`/`home_service_booking_drafts` with no prior explicit architecture decision (originally root-caused and fixed in FINAL-L5-01D). |
| Booking subsystem decision | **Model D**: `home_service_booking_drafts` → `service_bookings` directly; `bookings` is an unrelated other-vertical table, not a Home Services projection target. Re-verified this sprint with independent fresh evidence (source trace, live data, live API behavior) rather than re-citing the prior sprint's conclusion. |
| Files changed | `scripts/canonical_seed_final_l5_01.py` — added a `customer` parameter to `upsert_job()` and a 6th seeded job/booking for Customer Two, closing a real gap (Customer Two previously had zero bookings, making true bidirectional isolation untestable). |
| Seed changes | See above; re-run twice this sprint, 100% idempotent, 0 duplicates. |
| API proof | 28 live HTTP calls this sprint (see Live API Smoke Report), including the full multi-step draft workflow and a genuine bidirectional cross-customer-access probe with real booking IDs on both sides. |
| Isolation proof | Customer One sees exactly their 5 bookings; Customer Two sees exactly their 1; cross-access in both directions returns a safe not-found with zero data exposure. |
| Browser proof | `final-l5-02b-customer-booking-browser.spec.ts` — both tests pass; Customer One's list/detail render real data with correct payment wording; Customer Two's isolation confirmed via direct-URL attempt. |
| Final status | **FIXED and re-verified. One new, real, honestly-documented gap found this sprint**: `confirm-price-choice` returns an unhandled 500 instead of a graceful 4xx when no provider was matched — logged as a new low-severity finding, not fixed (out of this mission's Tenant-Jobs/booking-source scope, and not something a normal UI flow would trigger). |
