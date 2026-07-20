# CUSTOMER-L5-15 — Baseline Verification

Per this sprint's own instruction ("Do not trust prior reports without
repository and runtime proof"), every claim below was re-verified against
current repository state in this session.

## 1–10. Prior-sprint facts re-confirmed

- Authentication (`get_current_user`), canonical `ServiceBooking`/
  `ServiceJob` (`app/engines/final_records/models.py`), booking/job
  ownership checks, provider-acceptance state, technician-assignment
  state, tracking state (CUSTOMER-L5-13), parts-approval state
  (CUSTOMER-L5-14) — all unchanged and re-confirmed against current code,
  not carried over from memory.
- Baseline gates re-confirmed: `npx tsc --noEmit` 31 pre-existing errors,
  `npx jest` 95 suites / 634 tests passing, `npx eslint src` 0 errors/36
  warnings, `npx prettier --check` clean.

## 11–23. Central Finding — a real, complete cancellation/reschedule engine exists, but it is architecturally disconnected from the real canonical booking

This is the most consequential finding of this sprint, and a **new
variant** of the "orphaned engine" pattern seen in CUSTOMER-L5-10
(bargain), L5-13 (geo/tracking), and L5-14 (parts-request customer
decision) — in every one of those cases the gap was either a disabled
flag or a missing endpoint/status transition. Here, for the first time,
**the permissions are correctly wired for customers**, but the engine
operates on an entirely separate, disconnected data model.

### The real canonical booking pipeline (confirmed, unchanged since L5-11)

`POST /v1/customer/home-services/booking-drafts/{draftId}/confirm`
(`app/engines/home_service_booking/customer_router.py` lines 282–326)
calls `HomeServiceFinalCreationService.finalize()`
(`app/engines/final_records/creation_service.py`), which creates the
canonical `ServiceBooking` + `ServiceJob` rows. `final_records`'s own
`customer_router.py` (lines 38–232) is **read-only** — every route is a
`GET` (bookings list/detail, jobs, appointments, leads). Grepped
exhaustively: **no cancel or reschedule mutation exists anywhere that
operates on `ServiceBooking`/`ServiceJob`** reachable by a customer.

The only cancellation capability touching `ServiceJob` at all is
`POST /v1/provider/service-jobs/{job_id}/cancel`
(`app/engines/execution/home_service_router.py` lines 276–279,
`provider_router`) — **provider-only**, not reachable by
`get_current_user`-authenticated customer traffic through any customer
router.

### A separate, real, well-built cancellation/reschedule engine exists — `app/engines/booking/`

`app/engines/booking/router.py` (prefix `/v1/bookings`, 21 endpoints,
self-described as `"Booking Engine — Router... Zero business logic"`) has
a genuinely complete implementation:

- `POST /v1/bookings/{booking_id}/cancel` (line 155) — real atomic
  cancellation with a cancellation-window check
  (`DEFAULT_CANCELLATION_WINDOW_HOURS`, `booking/constants.py` line 54),
  `within_cancel_window` flag, tenant-configurable window via
  `SettingsService.resolve("booking_cancellation_window_hours", ...)`.
- `POST /v1/bookings/{booking_id}/reschedule/request` (line 246),
  `POST /v1/bookings/reschedule/{reschedule_id}/accept` (line 257, **tenant-only**),
  `POST /v1/bookings/reschedule/{reschedule_id}/reject` (line 266, **tenant-only**)
  — a real `BookingRescheduleRequest` model (`booking/models.py` lines
  129–143), max-reschedule-count guard
  (`MAX_RESCHEDULE_COUNT = 3`, `constants.py` line 55).
- `GET /v1/bookings/tenants/{tenant_id}/cancellation-policy` (line 310) —
  a real policy endpoint, but its payload is minimal:
  `{tenant_id, cancellation_window_hours, max_reschedule_count, policy}`
  where `policy` is a single hardcoded English sentence template
  (`service.py` line 1048: `f"Cancel ≥{window}h before appointment: full
  refund. Cancel <{window}h: reservation forfeited."`) — **no fee
  amount, no service-credit field, no refund-eligibility field, no
  currency, no reason model, no idempotency key support, no
  booking/job version/concurrency field anywhere in this engine's
  models** (grepped `version` across `booking/models.py` — zero matches).
- `app/core/permissions.py` line 608–612: the `"customer"` role
  genuinely includes `P.BOOKING_CANCEL` and `P.BOOKING_RESCHEDULE` — so a
  real customer JWT **can** call `POST /v1/bookings/{booking_id}/cancel`
  without a 403.

### Why this engine cannot be the real target — confirmed by data-flow tracing, not assumption

`BookingService.cancel_booking` (`booking/service.py` line 719) resolves
the booking via `select(Booking).where(Booking.id == booking_id)` —
`Booking` is `app.engines.booking.models.Booking`, the table
`bookings`, **a completely different table from `final_records`'s
`ServiceBooking`** (table `service_bookings`, per that model file).
Grepped `app/engines/final_records/creation_service.py` (the sole real
path that creates a canonical booking) for any reference to
`app.engines.booking` — **zero matches**. The real booking pipeline
never creates, updates, or reads a row in the `bookings` table. A real
customer, holding a real `ServiceBooking.id` returned by
`GET /v1/customer/my-activity/bookings/{id}`, who called
`POST /v1/bookings/{that-id}/cancel` would receive a 404
`BOOKING_NOT_FOUND` (`booking/service.py` line 724:
`if not b: raise NotFoundException("Booking", str(booking_id))`) —
**every single time**, because that ID space is never populated by the
real flow.

This is confirmed, not inferred: this client could technically compile
and ship a screen that calls `/v1/bookings/{bookingId}/cancel` with a
real `ServiceBooking.id`, and it would pass a shallow smoke test in a
sandbox with no seeded `bookings` row, and then 404 against any real
booking in the field. Building against this engine would be building a
convincing-looking fake.

### What this means for scope

There is **no real, reachable, customer-facing cancellation or
reschedule capability for the actual canonical booking/job pipeline**
this app is built against. This sprint documents this exhaustively
(see `contract-matrix.md`) and — following the same principle applied in
every previous sprint that hit a real capability gap (never fabricate a
plausible-looking substitute) — does not wire the client to
`app/engines/booking/`'s endpoints, since doing so would be building a
guaranteed-to-404 feature against production data. The existing,
already-honest `BookingDetailScreen` "Cancel or reschedule" informational
row (`actionCancelReschedule`/`actionCancelRescheduleNote`, in place
since CUSTOMER-L5-12) already reflects the correct, honest state: not
available, contact support. This sprint's real, safely-shippable
contribution is verifying and strengthening that honesty with full
source-level proof, and adding regression tests asserting no fake
cancel/reschedule action is ever rendered.

## Cross-check: independent background research pass

An independent background Explore agent reached the same conclusion via
its own source reads and additionally confirmed:

- A **third** parallel job model exists (`app/engines/field_ops/`, table
  `jobs`) with a generic staff-only `PUT /v1/jobs/{job_id}/status`
  status-transition endpoint that can reach `cancelled` — but
  `P.FIELD_OPS_JOBS_UPDATE` is granted only to the `"technician"` role,
  not `"customer"`, and no dedicated cancel endpoint exists there either.
- `execution/home_service_service.py`'s `cancel_job` (provider-only) does
  **not** cascade: it never nulls `ServiceJob.assigned_staff_id`, never
  touches `ServiceJobQuote`/`PartsRequest` rows, and never publishes any
  notification/event-bus event. A real, separate "unassign" method
  (`HomeServiceJobAssignmentService.cancel_assignment`,
  `home_service_assignment/service.py` lines 361–406) exists and is fully
  correct, but it is **never called** from any cancel/reschedule path —
  it is an independent, manually-triggered provider action only.
- `PARTS_STATUS_CANCELLED` (`execution/constants.py` line 151) is defined
  once and referenced nowhere else in the repository — a dead constant,
  matching the same "aspirational status with no service logic" pattern
  documented in every previous sprint's own gap analysis.
- `app/engines/quote_checklist/`'s real `cancel_quote` method exists but
  is never invoked by any booking/job cancellation path.
- The active `platform_notifications` engine's `EVT_*` registry
  (`event_registry.py`) has **zero** cancellation/reschedule event
  constants. An older, apparently-disused `app/engines/notification/`
  engine has `"booking_cancelled"`/`"booking_rescheduled"` seed-data
  strings with no confirmed emitter anywhere in the codebase.
- No cancel/reschedule endpoint anywhere (legacy `booking` engine
  included) supports or requires an `Idempotency-Key` header, and no
  optimistic-concurrency/version field exists on any booking or job model
  in the entire repository (`ServiceBooking`, `ServiceJob`, or the legacy
  `Booking`/`field_ops.Job`).
- The legacy `booking` engine's cancellation does perform a **real**
  financial-adjacent action: releasing or forfeiting a `CreditReservation`
  against `CustomerCreditBalance` (`platform_commerce/service.py` lines
  647–682) — an internal ledger credit, not a cash/payment-gateway
  refund. This reinforces that even if this engine were reachable, its
  financial model is far simpler than the spec's aspirational
  fee/refund/service-credit boundary (no per-cancellation fee amount, no
  refund-eligibility field, no currency field).

This cross-check changes no conclusion — it strengthens the finding that
no real, reachable cancellation or reschedule capability exists for the
customer app's actual canonical booking, and additionally proves that
even the *disconnected* legacy engine wouldn't satisfy this sprint's
fuller fee/credit/refund/idempotency/concurrency requirements even if it
were somehow wired to the right table.

## 24–26. Working tree

`git status`/`git diff --stat` reviewed before starting; no unrelated
changes present; only this sprint's own new files/doc additions are
introduced.
