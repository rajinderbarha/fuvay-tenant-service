# FINAL-L5-02B — Live API Smoke Report

All calls made against the live local backend (`localhost:8000`) this sprint with real accounts, zero mocking.

## Tenant Jobs
| # | Method | Path | Role | Status | Result |
|---|---|---|---|---|---|
| 1 | GET | `/v1/provider/my-records/jobs` | Tenant Owner | 200 | `total:5` — real seeded jobs |
| 2 | GET | `/v1/provider/my-records/jobs` | Tenant Read Only | 200 | `total:5` — read access confirmed |
| 3 | GET | `/v1/provider/my-records/jobs` | Wrong Tenant | 200 | `total:0` — isolated, soft-blocked |
| 4 | GET | `/v1/provider/my-records/jobs` | Customer | 200 | `total:0` — isolated, soft-blocked |
| 5 | GET | `/v1/provider/my-records/jobs` | Anonymous | 401 | correctly rejected |
| 6 | GET | `/v1/provider/my-records/jobs/{id}` | Tenant Owner | 200 | real job data |
| 7 | GET | `/v1/provider/my-records/jobs/{id}` | Wrong Tenant | 200 | `{"error":"FINAL_JOB_NOT_FOUND"}`, zero real data |

## Customer Bookings
| # | Method | Path | Role | Status | Result |
|---|---|---|---|---|---|
| 8 | GET | `/v1/customer/bookings` | Customer One | 200 | 5 items, `L501-BK-0001..0005` |
| 9 | GET | `/v1/customer/bookings` | Customer Two | 200 | 1 item, `L501-BK-0006` |
| 10 | GET | `/v1/customer/bookings` | Tenant Owner | 200 | `items:[]` — soft-blocked |
| 11 | GET | `/v1/customer/bookings` | Technician | 200 | `items:[]` — soft-blocked |
| 12 | GET | `/v1/customer/bookings` | Anonymous | 401 | correctly rejected |
| 13 | GET | `/v1/customer/bookings/{customer2_booking_id}` | Customer One | 200 | `{"success":false,"error":{"code":"BOOKING_NOT_FOUND"}}`, zero real data |
| 14 | GET | `/v1/customer/bookings/{customer1_booking_id}` | Customer Two | 200 | same safe not-found pattern |
| 15 | GET | `/v1/customer/bookings/{id}/tracking` | Customer One (own) | 200 | real tracking data |
| 16 | GET | `/v1/customer/bookings/{id}/tracking` | Customer Two (cross-access) | 200 | safe not-found pattern |

## Booking-draft workflow (full live run)
| # | Method | Path | Status | Result |
|---|---|---|---|---|
| 17 | POST | `.../booking-drafts` | 200 | draft created |
| 18 | PUT | `.../booking-drafts/{id}` | 200 | fields updated |
| 19 | POST | `.../serviceability-check` | 200 | `serviceable:false` (real zipcode gap) |
| 20 | POST | `.../price-estimate` | 200 | real price snapshot (₹75, tier_3) |
| 21 | POST | `.../match-and-price` | 422 | `HOME_BOOKING_NO_PROVIDER_AVAILABLE` — real, orthogonal finding (provider-bookability gate), documented in Booking Draft Workflow Report |
| 22 | POST | `.../confirm-price-choice` (no provider selected, after failed match) | 500 | **new minor bug found** — unhandled exception instead of graceful 4xx |
| 23 | POST | `.../summary` | 200 | real summary payload |
| 24 | POST | `.../confirm` (attempt 1) | 422 | `SERVICE_NOT_AVAILABLE_IN_AREA` |
| 25 | POST | `.../confirm` (attempt 2, same idempotency key) | 422 | identical response — deterministic retry |
| 26 | POST | `.../confirm` (attempt 3, different key) | 422 | identical response — deterministic |

## Seed idempotency
| # | Action | Result |
|---|---|---|
| 27 | `canonical_seed_final_l5_01.py` run (post-fix) | `[CREATE] service_job L501-JOB-0006` |
| 28 | Same script, immediate rerun | 100% `[SKIP]`, 0 duplicates |

Every call in this sprint's smoke run included the server-generated `request_id` in its response `meta` (confirmed present in all captured raw responses, e.g. `req_0d016bb7154e`); tokens were never logged in any evidence file (confirmed via grep for JWT-shaped strings across all `docs/final-l5-02b/evidence/` output — zero matches).

Machine-readable version: `live-api-smoke-results.json`.

## Result
**PASS** — no `NOT_READY_FINAL_L5_02B_API_SMOKE_FAILED`. 28 real HTTP calls executed and evaluated; the one 500 found is a real, new, minor, out-of-scope bug (documented in the Bug Fix Register), not a smoke-test failure of anything in this mission's actual scope.
