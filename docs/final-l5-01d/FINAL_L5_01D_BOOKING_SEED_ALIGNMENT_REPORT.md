# FINAL-L5-01D — Booking Seed Alignment Report

## Change made
`scripts/canonical_seed_final_l5_01.py::upsert_job()` rewritten to create, per job:
1. A minimal `home_service_booking_drafts` row (`status='converted'`) — satisfies `service_bookings.draft_id`'s NOT-NULL requirement, mirroring the real customer booking-draft flow.
2. A `service_bookings` row (`booking_number='L501-BK-NNNN'`, correct `customer_id`/`tenant_id`/`category_id`/`offering_id`) — the canonical booking record.
3. `service_jobs.booking_id` now points at the `service_bookings.id` (previously pointed at a `bookings.id`).

The `bookings` table is **no longer written to by this seed at all** — satisfying "do not seed both bookings tables blindly." `bookings` keeps whatever role it has for other engines, untouched.

## Verification

| Requirement | Result |
|---|---|
| Deterministic | Yes — stable `job_number` lookup key unchanged |
| Idempotent | **Proven** — reran the seed after the fix; 100% `[SKIP]` on every job/draft/booking, `jobs: 0` in summary |
| No duplicate bookings | Confirmed — `service_bookings` count stayed at 5 across the rerun |
| No orphan `service_jobs` | Confirmed — `service_jobs.booking_id` matches a real `service_bookings.id` for all 5 jobs (verified via SQL join, 5/5 match) |
| Customer One has usable booking history | **Confirmed live**: `GET /v1/customer/bookings` as Customer One now returns 5 real items (`L501-BK-0001` through `0005`) — previously empty |
| Customer Two isolation remains testable | **Confirmed live**: `GET /v1/customer/bookings` as Customer Two returns 0 items — zero leakage |
| Rerunning seed does not create duplicate projections | Confirmed — idempotency rerun above |

## Not fabricated
No booking rows were invented to "make the UI non-empty" independent of real job data — every `service_bookings` row corresponds 1:1 to a real canonical `service_jobs` row that FINAL-L5-01 already established as legitimate deterministic test data. This is a **correction of which table the existing legitimate data was written to**, not new fabricated content.

## Result
**PASS.** BUG-L502-006 (customer bookings seed gap) is fixed, verified idempotent, and verified live via the real customer-facing API.
