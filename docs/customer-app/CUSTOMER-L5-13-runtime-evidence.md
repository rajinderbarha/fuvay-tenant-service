# CUSTOMER-L5-13 — Runtime Evidence

## Live Backend Certification: NOT PERFORMED

Identical constraint to every previous sprint: this environment has no
running backend server, no reachable database, and no seeded
`ServiceJobExecutionEvent` data. None of the following were done:

- No real `GET /v1/customer/service-jobs/{jobId}/tracking` request was
  made against a live server with a job that has genuinely progressed
  through `on_the_way → reached_site → inspection_started → ... →
  work_done`.
- No real staff-triggered execution transition (`POST /v1/staff/service-jobs/{id}/on-the-way`,
  etc.) was exercised to observe the resulting real
  `ServiceJobExecutionEvent` rows and confirm this client's timeline
  renders them correctly end to end.
- No request IDs, status codes, or screenshots from a live run exist.

## What Was Verified Instead

- The exact real backend contract, via direct source-code reading of
  `execution/home_service_service.py`, `home_service_router.py`,
  `models.py`, `constants.py`, `home_service_assignment/staff_model.py`,
  `geo/models.py`, `geo/service.py`, `customer_reviews/models.py`,
  `public_router.py`, `app/engine_registry/registry.py`, `app/main.py` —
  cross-checked by an independent background research pass that
  additionally confirmed the orphaned `geo` engine, the absent
  websocket/SSE transport, and the unexposed `StaffRatingSummary`
  aggregate.
- Every client-side code path (execution-timeline parsing including the
  real in-progress shape, structural stripping of `notes`/`actor_role`/
  `id`/`job_id`, empty-timeline and per-item-resilience cases; event-label
  mapping including every real, confirmed-emitted event type and the
  fail-safe unmapped case; the shared status registry's 8 newly-added
  real execution statuses) is exercised by 9 new unit tests using
  fixtures shaped exactly like the real backend's actual response bodies
  (per the exact dict literals and constant values read from source).
- `npx tsc --noEmit`: 31 errors, 0 new (identical to the pre-sprint
  baseline).
- `npx jest`: 617/617 passing (608 carried forward + 9 new).
- `npx eslint src`: 0 errors, 36 pre-existing warnings (baseline
  unchanged).
- `npx prettier --check`: clean on every new/changed file.

## Honest Gate Impact

Per this sprint's own acceptance standard, this cannot claim a hard PASS:
live runtime proof was not possible in this environment, and a
substantial share of the spec's aspirational model (technician profile,
live GPS, map rendering, ETA, route, masked-call, tracking sessions,
real-time transport) is confirmed absent or architecturally unreachable
from this app's real pipeline — verified exhaustively across two
independent research passes reaching the same conclusions. The gate
decision reflects PARTIAL.

## What Would Close the Environment Gap

Run the actual backend (`uvicorn app.main:app`) against a seeded database
with a real assigned technician (`ProviderTeamMember` linked via
`ServiceJob.assigned_staff_id`), then exercise the real staff-facing
execution endpoints in sequence
(`/on-the-way`, `/reached-site`, `/start-inspection`,
`/complete-inspection`, `/start-service`, `/work-done`) and confirm each
produces a real `ServiceJobExecutionEvent` row that this sprint's
`ServiceTrackingScreen` renders correctly, in order, with the correct
customer-safe label and timestamp — walking Home → My Bookings → Booking
Detail → "Track provider" → Service Tracking end to end on a real device.
