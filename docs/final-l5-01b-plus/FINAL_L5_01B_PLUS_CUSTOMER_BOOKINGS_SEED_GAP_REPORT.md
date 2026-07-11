# FINAL-L5-01B-PLUS — Customer Bookings Seed Gap (root-caused)

## Finding
Customer One's real browser session shows "No bookings yet" on `/customer/bookings` despite being the customer on all 5 FINAL-L5-01 canonical jobs.

## Root cause (precisely diagnosed)
The canonical customer-facing endpoint `GET /v1/customer/bookings` (`app/engines/home_service_assignment/customer_router.py:56`) queries `ServiceBooking` — a model mapped to the **`service_bookings`** table (`app/engines/final_records/models.py:16`).

FINAL-L5-01's `scripts/canonical_seed_final_l5_01.py` inserted its 5 booking rows into the **`bookings`** table (used to satisfy `service_jobs.booking_id`'s NOT-NULL constraint) — a **different table** from `service_bookings`. Confirmed via direct query:
```
service_bookings count: 0
bookings count: 5
```
This is a genuine **seed-data gap**, not a backend defect: the backend endpoint is correct and canonical; the seed script simply never populated the table this endpoint reads from.

## Why not fixed this pass
`service_bookings` has additional NOT-NULL columns not present on `bookings` — notably `draft_id` (NOT NULL, no default), `booking_number`, `category_id`, `offering_id` — `draft_id` appears to FK into a customer-booking-draft subsystem (`app/engines/customer_flow` per FINAL-L5-01B's memory of `CustomerBookingDraft`) that would need its own seed rows first. Extending the canonical seed correctly requires understanding that subsystem's constraints, which was not done this pass given time constraints — attempting a rushed insert risks violating an FK/constraint incorrectly.

## Recommendation
A future canonical-seed pass should either:
1. Populate `service_bookings` (with valid `draft_id` references) alongside `bookings`, or
2. Confirm whether `bookings` and `service_bookings` are meant to be the same logical concept that should be consolidated (worth a schema review — two tables both named "bookings"-ish serving overlapping purposes is itself a duplication smell, consistent with this session's other findings).

## Severity assessment
Low risk, medium annoyance: no security or data-integrity issue — purely an empty-state display gap in the canonical data set. Tenant-facing jobs data (queried via `/v1/provider/service-jobs/assignable`, backed by `service_jobs`) is unaffected and confirmed working.
