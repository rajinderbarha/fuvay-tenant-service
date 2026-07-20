# Known Limitations

1. **Residual bootstrap risk (disclosed, not fixed)**: a `tenant_owner` can still create a
   Booking naming an arbitrary REAL customer via `POST /v1/bookings` (which never validates
   `customer_id` against the User table) and then unilaterally confirm it themselves via
   `POST /v1/bookings/{id}/confirm` (which requires no customer participation), reaching
   `BS.CONFIRMED` — now-qualifying status — without genuine customer contact. Closing this would
   require modifying `BookingService.create_booking`/`confirm_booking` in the booking engine,
   which is outside this slice's scope (confined to the `create_job` relationship helper). This
   is the reason full customer-authority-provenance closure remains blocked — see approval-gate.md.
2. `cancelled`/`voided` Bookings are excluded from relationship evidence even in cases where they
   WERE genuinely confirmed before cancellation — current status alone cannot distinguish this
   from a booking cancelled before ever reaching confirmation, and querying `BookingStatusHistory`
   to disambiguate was not implemented this slice (product-decisions-required.md item 3). This is
   a conservative, safe over-exclusion, not a security gap.
3. Concurrency race window for booking/repair duplicate guards remains
   (`CONCURRENCY_RISK_DOCUMENTED`, carried over from Slice 2F-14D/E, unchanged).
4. `JobMedia` internal/customer-visible schema, legacy checklist deprecation, legacy quote-surface
   consolidation, `booking_id`/`parent_job_id` documented coexistence semantics, address
   derivation from booking — all carried over from prior slices, unchanged.
