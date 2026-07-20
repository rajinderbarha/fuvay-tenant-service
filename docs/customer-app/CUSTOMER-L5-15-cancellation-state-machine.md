# CUSTOMER-L5-15 — Cancellation State Machine

## For the canonical booking

Not applicable — no cancellation state machine exists for
`ServiceBooking`/`ServiceJob` reachable by a customer. The only real
transition is provider-initiated (`execution/home_service_service.py`'s
`cancel_job`, provider-role only): any non-terminal `JS_*` status →
`JS_CANCELLED`, via `_set_status`'s generic `JOB_TRANSITIONS` validation
— the same generic mechanism CUSTOMER-L5-13 already documented for every
other job-status transition, not a dedicated cancellation flow.

## For the disconnected legacy `booking` engine (reference only)

```
draft/pending_confirmation/pending/confirmed/scheduled/dispatching/in_progress
  ──(customer or tenant_owner: cancel, if status not terminal)──► cancelled [terminal]
```

`TERMINAL_BOOKING_STATUSES = {completed, cancelled, expired, voided,
rejected, converted_to_job}` (`booking/constants.py` lines 37–40) — all
block a further cancel attempt with 409 `BOOKING_CANNOT_BE_CANCELLED`.
No `CANCELLATION_PENDING`/`REQUIRES_APPROVAL` intermediate state exists
— this engine's cancellation is always atomic and immediate, never a
two-step approval flow. There is no `ALREADY_CANCELLED` distinct from
the generic terminal-status 409 (same error code either way).

## This client's implementation

`features/bookings/domain/cancellation-reschedule-availability.ts`
exports `isCancellationAvailable(bookingStatus): boolean`, unconditionally
`false` for every status — the verified-correct state, not a placeholder.
`BookingDetailScreen.tsx` renders the existing "Cancel or reschedule"
informational row whenever this (and the reschedule equivalent) returns
false, i.e. always, for every real booking status observed in
`booking-status-registry.ts` (pending_assignment through the L5-14
quote-decision statuses). Covered by
`cancellation-reschedule-availability.test.ts`.
