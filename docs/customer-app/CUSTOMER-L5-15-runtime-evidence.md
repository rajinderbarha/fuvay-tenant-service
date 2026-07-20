# CUSTOMER-L5-15 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED (and not applicable to a mutation)

Identical environment constraint to every previous sprint: no running
backend/database is reachable here. But unlike every previous sprint,
this sprint has **no real mutation to certify against a live backend even
in principle** — the central finding (baseline-verification.md) is that
no customer-facing cancellation or reschedule endpoint exists for the
canonical `ServiceBooking`/`ServiceJob` pipeline at all.

## What Was Verified Instead

- Exhaustive, cross-checked source reading (own direct reads +
  independent background research agent, reaching the same conclusion
  independently) of: `app/engines/final_records/customer_router.py`
  (confirmed read-only), `app/engines/execution/home_service_router.py`
  (confirmed only provider-role cancel, only customer-role tracking),
  `app/engines/home_service_assignment/{customer_router.py,service.py,
  provider_router.py}` (confirmed read-only customer surface, confirmed
  real-but-unwired `cancel_assignment`), `app/engines/booking/
  {router.py,service.py,models.py,constants.py}` (confirmed real,
  complete, but disconnected cancellation/reschedule engine),
  `app/engines/quote_checklist/quote_service.py` (confirmed unwired
  `cancel_quote`), `app/core/permissions.py` (confirmed `"customer"` role
  does hold `P.BOOKING_CANCEL`/`P.BOOKING_RESCHEDULE` — a permission
  correctly granted for an engine that is nonetheless unreachable for
  real bookings), `app/engines/platform_notifications/event_registry.py`
  (confirmed zero cancellation/reschedule events registered).
- `npx tsc --noEmit`: 31 errors, 0 new.
- `npx jest`: 636/636 passing (634 carried forward + 2 new).
- `npx eslint src`: 0 errors, 36 pre-existing warnings.
- `npx prettier --check`: clean.

## Honest Gate Impact

PARTIAL, for a different reason than every previous sprint's PARTIAL:
previous sprints' PARTIAL reflected an inability to run a live server in
this environment while still having real, working client code to show.
This sprint's PARTIAL additionally reflects that **no real backend
capability exists to build client code against in the first place** —
verified through static source analysis alone, cross-checked by an
independent research pass reaching the same conclusion. There is nothing
a live backend run in this environment could have proven that static
analysis has not already conclusively shown (a 404 against a
disconnected table is not evidence a live run would meaningfully add
beyond the direct code trace already performed).

## What Would Close the Environment Gap

For cancellation/reschedule to become certifiable, a backend engineer
would first need to either (a) add real cancel/reschedule endpoints
operating on `ServiceBooking`/`ServiceJob` with a fee/refund/service-
credit model, idempotency support, and a version/concurrency field, or
(b) migrate the legacy `booking` engine to operate on the canonical
tables. Only after either exists would a live-backend run against a real
customer, real booking, and real job be a meaningful next step.
