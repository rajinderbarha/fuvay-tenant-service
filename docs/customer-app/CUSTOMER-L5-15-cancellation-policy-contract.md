# CUSTOMER-L5-15 — Cancellation Policy Contract

## For the canonical booking (`ServiceBooking`/`ServiceJob`)

**No real endpoint exists.** There is no cancellation-eligibility, policy,
reason-catalog, fee, service-credit, or refund endpoint reachable by a
customer for the actual booking this app creates and displays. See
`baseline-verification.md`'s Central Finding.

## For the disconnected legacy `booking` engine (documented for completeness, NOT implemented client-side)

`GET /v1/bookings/tenants/{tenant_id}/cancellation-policy`
(`app/engines/booking/router.py` line 310) returns:

```json
{
  "tenant_id": "...",
  "cancellation_window_hours": 24,
  "max_reschedule_count": 3,
  "policy": "Cancel ≥24h before appointment: full refund. Cancel <24h: reservation forfeited."
}
```

`POST /v1/bookings/{booking_id}/cancel` (`router.py` line 155):

- Requires `P.BOOKING_CANCEL` (granted to `"customer"` role,
  `app/core/permissions.py` line 611).
- Body: raw JSON, only `reason` read (defaults to `"Customer request"` if
  omitted — no validation, no reason-code catalog).
- 409 `BOOKING_CANNOT_BE_CANCELLED` if `Booking.status` is terminal
  (`completed, cancelled, expired, voided, rejected, converted_to_job` —
  `booking/constants.py` lines 37–40). Note `converted_to_job` is
  terminal for *this* cancel path — once a booking becomes a job, this
  endpoint can no longer touch it at all.
- Computes `within_cancel_window` against a tenant-configurable
  `booking_cancellation_window_hours` setting (default 24h).
- **Financial effect**: releases or forfeits a `CreditReservation`
  against `CustomerCreditBalance` (`platform_commerce/service.py` lines
  647–682) — an internal credit-ledger operation, not a cash refund. No
  per-cancellation fee *amount* field exists anywhere; the only
  consequence is "reservation released" (within window) or "reservation
  forfeited" (outside window).
- No `Idempotency-Key` support. No optimistic-concurrency/version field.
- Publishes a raw event-bus event (`"booking.cancelled"`) with no
  confirmed real notification-template consumer.

## Why this is not implemented client-side

Confirmed via direct data-flow tracing (not assumption) that
`Booking.id` (this engine's own primary key) and `ServiceBooking.id` (the
real canonical booking's ID, the only ID this client ever holds) are
different ID spaces with zero overlap — `HomeServiceFinalCreationService.
finalize()` never creates a row in the `bookings` table. Calling this
endpoint with a real booking ID returns 404 every time. See
`contract-matrix.md`.

## What a correct backend fix would look like (for a future sprint)

Either (a) add real cancel/reschedule endpoints operating directly on
`ServiceBooking`/`ServiceJob` with a proper fee/refund/service-credit
model, idempotency support, and a version/concurrency field, or (b)
migrate the legacy `booking` engine's logic to operate on
`ServiceBooking`/`ServiceJob` instead of its own disconnected table. This
sprint does not attempt either — both are backend architecture decisions
outside a client sprint's scope.
