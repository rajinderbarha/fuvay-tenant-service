# CUSTOMER-L5-12 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no seeded
`ServiceBooking`/`ServiceJob`/`ServiceJobAssignment` data. None of the
following were done:

- No real `GET /v1/customer/bookings` list request was made against a
  live server, with real pagination across multiple pages.
- No real booking detail/timeline fetch was observed against a live
  booking that has progressed through `pending_assignment → assigned →
  accepted → scheduled`.
- No real technician-assignment transition (`assign_job`/
  `technician_accept_job`/`technician_reject_job`) was triggered to
  observe the resulting real `ServiceJobAssignmentEvent` rows and confirm
  this client's timeline renders them correctly end to end.
- No real notification deep link was opened (no real push channel exists
  to send one from — `notification-deep-links.md`).
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract, via direct source-code reading of
  `home_service_assignment/customer_router.py`, `service.py`,
  `models.py`, `constants.py`, `final_records/models.py`,
  `final_records/constants.py`, `execution/home_service_service.py`,
  `execution/home_service_router.py`, `app/engines/platform_notifications/channel_providers.py`
  — cross-checked by an independent background research pass that
  additionally identified the decisive corrections (real reachable status
  set, real `ServiceJobAssignmentEvent` timeline, permanently-stubbed push
  channel, and the two unrelated decoy legacy tables).
- Every client-side code path (list-page parsing and honest
  `mayHaveMore` inference; detail parsing including the real, distinct
  `{success:false, error:{...}}` shape; tracking parsing including the
  synthetic first row and per-item resilience; review-status parsing;
  status registry — every real reachable status plus the defined-but-
  unreachable ones plus the unknown-status fail-safe; group mapping) is
  exercised by 23 new unit tests using fixtures shaped exactly like the
  real backend's actual response bodies (per the exact code read from
  source).
- `npx tsc --noEmit`: 31 errors, 0 new (identical to the pre-sprint
  baseline).
- `npx jest`: 608/608 passing (585 carried forward + 23 new, after fixing
  two pre-existing tests that referenced routes this sprint legitimately
  promoted to production).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (baseline
  unchanged).
- `npx prettier --check`: clean on every new/changed file.

## Honest Gate Impact

Per this sprint's own acceptance standard, this cannot claim a hard PASS:
live runtime proof was not possible in this environment, and a real,
substantial share of the spec's aspirational model (dispatched/
in-progress/completed statuses, live tracking, action-availability
contract, push-notification delivery, cancellation/reschedule execution)
describes capabilities confirmed absent or unreachable in this real
backend today — verified exhaustively, not assumed, across two
independent research passes reaching the same conclusions. The gate
decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with: a confirmed `ServiceBooking` with no job yet (to exercise the
`job_status`-absent detail/list rendering), a second with an assigned
technician who then accepts (to exercise a real, multi-event
`ServiceJobAssignmentEvent` timeline end to end), and a third with a
rejected/reassigned technician (to exercise the "back to
pending_assignment" real transition and its timeline entries). Walk My
Bookings → filter Active/Past → open a booking's detail → confirm the
real timeline renders each real event in order → pull-to-refresh →
confirm updated state after a real backend-side technician-acceptance
transition.
