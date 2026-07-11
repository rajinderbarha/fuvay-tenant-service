# FINAL-L5-01D — Customer Booking Source-of-Truth Decision

## Decision: **A — `service_bookings` is canonical for Home Services**

## Evidence against each decision criterion

| Criterion | Finding |
|---|---|
| Which table receives real customer booking writes (for Home Services)? | `service_bookings`, via `final_records/creation_service.py::confirm_home_service_draft()` — the actual, live confirmation-flow code that runs when a real customer completes a booking |
| Which table links correctly to `service_jobs`? | `service_bookings` — **direct code proof**: `creation_service.py:150`, `ServiceJob(booking_id=booking.id, ...)` where `booking` is a `ServiceBooking` instance. `bookings` has zero code creating a `service_jobs` row from it. |
| Which table is used by tracking? | `service_bookings` (`final_records/confirm_router.py`, `execution/home_service_service.py`) |
| Which table is used by cancellation? | Not independently re-verified this sprint (time constraint) — `service_bookings.status`/`assignment_status` columns support a cancellation state; `bookings` was not found wired to any Home Services cancellation flow |
| Which table is used by reviews? | `service_bookings` — `customer_reviews/eligibility_service.py` imports `ServiceBooking` directly |
| Which table is tenant-scoped correctly? | Both have `tenant_id` columns; `service_bookings` is the one actually populated per-tenant by the real creation flow |
| Which table is used by the current customer APIs? | `service_bookings` — `GET /v1/customer/bookings` (`home_service_assignment/customer_router.py:52-57`) queries `ServiceBooking` |
| Which table has current migrations and tests? | `service_bookings`: migration 037 (Sprint 19, "Booking Confirmation → Final Record Creation" — the dedicated feature sprint for this exact flow, per project history) |

## Not chosen based on row counts
At the time this decision was made, `bookings` had 5 rows (from FINAL-L5-01's seed) and `service_bookings` had 0 — the *opposite* of what row-count-only reasoning would suggest. The decision is based entirely on **which table the real, live application write path actually uses**, confirmed via direct source inspection of `creation_service.py`, not on which table happened to contain data.

## What `bookings` actually is
A separate, legitimate, generic booking-request concept used by other engines (`ai_chat`, `ai_conversation`, `admin_customers_router`, `compliance`, `dashboard_command_center`) — not a Home-Services-specific table, and not wrong to have rows in it; it's simply **not** what `service_jobs`/customer-tracking/reviews/complaints read from for Home Services. FINAL-L5-01's seed incorrectly assumed `bookings` was the right table to satisfy `service_jobs.booking_id`'s NOT-NULL constraint — an honest mistake, now corrected.

## Consumer trace confirms this is safe to fix
`service_jobs.booking_id` has **no database-level FK constraint** (confirmed via `pg_constraint` query — consistent with FINAL-L5-01B's ~190-table missing-FK finding), so repointing it from `bookings.id` to `service_bookings.id` values required no migration, no constraint changes, and broke nothing at the DB level — only the canonical seed script's own INSERT logic needed correction.
