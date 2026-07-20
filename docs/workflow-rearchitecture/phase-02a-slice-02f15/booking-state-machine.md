# Booking State-Machine Integrity

## Transition map (unchanged, from `app.engines.booking.constants.BOOKING_TRANSITIONS`)

```
DRAFT               -> [PENDING_CONFIRMATION, PENDING, CANCELLED]
PENDING_CONFIRMATION -> [CONFIRMED, REJECTED, CANCELLED, EXPIRED]
PENDING              -> [CONFIRMED, REJECTED, CANCELLED, EXPIRED]
CONFIRMED            -> [CONVERTED_TO_JOB, SCHEDULED, CANCELLED]
REJECTED             -> []
CONVERTED_TO_JOB     -> [COMPLETED]
SCHEDULED            -> [DISPATCHING, CANCELLED]
DISPATCHING          -> [IN_PROGRESS, CANCELLED]
IN_PROGRESS          -> [COMPLETED, CANCELLED]
COMPLETED            -> []
CANCELLED            -> []
VOIDED               -> []
```

None of this was modified this slice — the state machine itself was already correct
(unchanged since prior slices' review). This slice's fix operates entirely BEFORE the state
machine is entered (at `create_booking`, before any `Booking` row exists) and does not add,
remove, or alter any transition.

## Verified for confirmation specifically (unchanged, pre-existing, re-confirmed this slice)

- **Legal source states**: `PENDING`, `PENDING_CONFIRMATION` only (`confirm_booking`'s own
  explicit check, `service.py:680-683`).
- **Illegal source states**: any other status raises `BOOKING_INVALID_STATUS_TRANSITION` (422).
- **Repeated confirmation**: a booking already `CONFIRMED` is no longer in
  `(PENDING, PENDING_CONFIRMATION)`, so a second confirm call raises the same 422 — confirmed
  idempotent-safe (not silently double-processed).
- **Cancelled/rejected/expired**: none of these are in `(PENDING, PENDING_CONFIRMATION)`, so
  confirmation from any of them is rejected.
- **Converted**: `CONVERTED_TO_JOB` is not in the legal source set — confirmation after
  conversion is rejected.
- **Result state**: always exactly `BS.CONFIRMED`.

## No new tests needed for state-machine mechanics

The transition legality checks themselves were not modified this slice (only the
CREATION-time customer/relationship validation was added, upstream of any status check) — no
regression risk, confirmed via the full `test_step4_booking.py` suite (44 tests) passing
unmodified.
