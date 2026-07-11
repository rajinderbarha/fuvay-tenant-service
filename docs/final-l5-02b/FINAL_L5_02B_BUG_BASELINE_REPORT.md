# FINAL-L5-02B — Bug Register Baseline

## BUG-L502-005
| Field | Value |
|---|---|
| Bug ID | BUG-L502-005 |
| Severity | High |
| Application | Tenant Portal (`frontend/tenant-portal`) |
| Route/page | `/jobs`, `/jobs/[id]`, `/dashboard`, `/staff/[id]` |
| Frontend file and line | `lib/api.ts:246-290` (legacy `jobsApi`); consumers: `components/dashboard/HomeServiceDashboard.tsx:15-16` (dashboard widget), `app/(tenant)/staff/[id]/page.tsx:26` (staff detail "recent jobs") |
| Backend endpoint/table involved | Legacy `GET /v1/jobs` → `jobs` table (field_ops domain), which is **permanently empty** (0 rows) since the canonical seed writes only to `service_jobs`/`service_bookings` |
| Observed browser behavior | Tenant Jobs list/detail pages were already migrated in FINAL-L5-01D and correctly show real data. However, the **Tenant Dashboard's "Recent Jobs"/SLA widgets and the Staff Detail page's "Recent Jobs" widget were still calling legacy `jobsApi.list()`/`jobsApi.slaAlerts()`**, which return empty/stale results because the backing `jobs` table has 0 rows — these widgets silently showed nothing instead of the 5 real seeded `service_jobs`. |
| Expected behavior | All Tenant Portal job displays read from the canonical `service_jobs` table via `/v1/provider/my-records/jobs`. |
| Root cause | The FINAL-L5-01D migration covered the main Jobs list/detail pages but missed two other active consumers of the same legacy `jobsApi` module elsewhere in the app (dashboard widget, staff detail widget) — a consumer-scan gap, not a re-regression of the already-fixed pages. |
| Current status | **FIXED this sprint.** Both remaining consumers migrated to `serviceJobsApi`. Zero active `jobsApi.` references remain anywhere in `frontend/tenant-portal` (confirmed via source grep). See Bug Closure Report. |

## BUG-L502-006
| Field | Value |
|---|---|
| Bug ID | BUG-L502-006 |
| Severity | Medium (data-completeness / architectural clarity, not security) |
| Application | Backend (`app/engines/home_service_booking`, `app/engines/final_records`, `app/engines/home_service_assignment`) + Customer App |
| Route/page | `/v1/customer/bookings*`, `/v1/customer/home-services/booking-drafts/*`, Customer App `/customer/bookings` |
| Frontend file and line | `frontend/customer-app/lib/api/customer-home-services.ts` (already correctly wired, see below) |
| Backend endpoint/table involved | `bookings` (0 rows, not used for Home Services), `service_bookings` (5 rows, canonical), `home_service_booking_drafts` (74 rows, real draft table — **not** `booking_drafts` as informally referenced; that table does not exist) |
| Observed browser behavior | This bug was already root-caused and fixed in FINAL-L5-01D: the canonical seed originally wrote to the generic `bookings` table while the real customer-facing endpoint reads `service_bookings`, causing an empty customer booking list. |
| Expected behavior | Customer booking list/detail/tracking show real seeded data sourced from the single canonical table. |
| Root cause | Table naming ambiguity across three candidate tables (`bookings`, `service_bookings`, `home_service_booking_drafts`) with no prior explicit architecture decision; the original seed guessed the generic `bookings` table. |
| Current status | **Already fixed in FINAL-L5-01D, re-verified this sprint** with fresh evidence: live DB query confirms `bookings=0` / `service_bookings=5` rows post-reset, backend code trace confirms `home_service_assignment/customer_router.py` imports and queries `ServiceBooking` exclusively (not `Booking`), and live browser regression confirms Customer One sees all 5 real bookings with correct data. This sprint formalizes the decision (Part 11) and traces the full draft→booking→job lifecycle (Part 9-10) with fresh live evidence rather than re-asserting the FINAL-L5-01D finding from memory alone. |
