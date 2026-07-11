# FINAL-L5-02B — Updated Frontend/Backend Contract Matrix

| Application | Feature/page | Client function | Method | Canonical path | Backend handler | Source table | Status | Browser verification |
|---|---|---|---|---|---|---|---|---|
| Tenant Portal | Jobs list | `serviceJobsApi.list` | GET | `/v1/provider/my-records/jobs` | `final_records/provider_router.py` | `service_jobs` | CANONICAL_ACTIVE | Verified this sprint (network capture, 0 legacy calls) |
| Tenant Portal | Job Detail | `serviceJobsApi.get` | GET | `/v1/provider/my-records/jobs/{id}` | `final_records/provider_router.py` | `service_jobs` | CANONICAL_ACTIVE | Verified this sprint |
| Tenant Portal | Job actions (assign/schedule/cancel) | `serviceJobAssignmentApi.*` | POST | `/v1/provider/service-jobs/{id}/*` | assignment sub-router | `service_job_assignments` | CANONICAL_ACTIVE | Verified FINAL-L5-01D, unchanged |
| Tenant Portal | Dashboard "Recent Jobs" widget | `serviceJobsApi.list` | GET | `/v1/provider/my-records/jobs` | `final_records/provider_router.py` | `service_jobs` | **CANONICAL_ACTIVE — migrated this sprint (was legacy `/v1/jobs`)** | Verified this sprint |
| Tenant Portal | Staff Detail "Recent Jobs" widget | `serviceJobsApi.list` | GET | `/v1/provider/my-records/jobs` | `final_records/provider_router.py` | `service_jobs` | **CANONICAL_ACTIVE — migrated this sprint (was legacy `/v1/jobs`)** | Verified via source + tsc (page not separately browser-tested this sprint) |
| Customer App | Booking list | `getCustomerBookings` | GET | `/v1/customer/bookings` | `home_service_assignment/customer_router.py` | `service_bookings` | CANONICAL_ACTIVE | Verified this sprint (5/1 real items for Customer One/Two) |
| Customer App | Booking Detail | `getCustomerBookingDetail` | GET | `/v1/customer/bookings/{id}` | `home_service_assignment/customer_router.py` | `service_bookings` + `service_jobs` | CANONICAL_ACTIVE | Verified this sprint |
| Customer App | Tracking | `getCustomerBookingTracking` | GET | `/v1/customer/bookings/{id}/tracking` | `home_service_assignment/customer_router.py` | `service_bookings` + `service_jobs` | CANONICAL_ACTIVE | Verified this sprint |
| Customer App | Cancellation | `cancelCustomerBooking` | — | **no endpoint exists** | — | — | **DOCUMENTED_GAP** (typed stub rejects with explanation) | N/A |
| Customer App | Review | `submitCustomerBookingReview` | POST | `/v1/customer/bookings/{id}/rating` | `home_service_assignment/customer_router.py` | `service_bookings` | CANONICAL_ACTIVE | Verified via code inspection this sprint (not live-submitted) |

## Required expectations
- **0 active Tenant Jobs calls to `/v1/jobs`** — **met** (confirmed via live browser network capture + source grep).
- **0 ambiguous customer booking source rows** — **met** (`service_bookings` is the sole, unambiguous canonical source; `bookings` confirmed unrelated/unused for this domain).

Machine-readable version: `updated-contract-matrix.json`.
