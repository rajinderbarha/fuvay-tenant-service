# Provider-Assisted Booking Provenance

## The rule
For a Booking created via the provider-assisted path (Slice 2F-15: a `tenant_owner` calls `create_booking` naming a `customer_id`):

1. **The creation actor remains provider, permanently.** `BookingStatusHistory`'s creation row (`from_status IS NULL`) records `changed_by_role == "tenant_owner"` at the moment of creation, and this is never rewritten — `BookingStatusHistory` is append-only (no `UPDATE` statement exists against this table anywhere in the codebase, confirmed via grep for `update(BookingStatusHistory)`/`.update()` calls).
2. **The Booking itself is never labelled customer-created.** No later action can change what row was written at creation time; later customer activity (cancellation, reschedule) writes NEW rows with `from_status` populated, never touching or superseding the original `NULL` row.
3. **Its authority derives from independent prior relationship evidence at the time it was created.** `BookingService.create_booking`'s own relationship-requirement check (added 2F-15, tightened 2F-15A) already requires this evidence to exist BEFORE the assisted Booking can be created at all — enforced via the identical `from_status IS NULL AND changed_by_role == "customer"` query against OTHER Bookings/Jobs for that customer+tenant.
4. **That evidence excludes the current Booking** — trivially true, since the relationship check runs before the new Booking is even persisted (`db.add(booking)` happens after the check, not before).

## Rechecking vs. persisted provenance
Without a new provenance column (out of scope), this slice's design **rechecks independent evidence at each authority-dependent action** (`convert_to_job`, direct `create_job(booking_id=...)`) rather than persisting a one-time "trusted" flag on the Booking. This is deliberate:

- A persisted flag would need to be set once and trusted forever, creating a new attack surface (a `flag=True` written once could become stale if the underlying evidence Booking/Job it depended on is later found to be fraudulent, and there is no revocation mechanism without a migration).
- Rechecking is idempotent and always reflects the CURRENT state of the customer's relationship evidence — read-only, no new write path, no schema change.
- The cost is an extra query per authority-dependent action, judged acceptable given these are low-frequency administrative operations (Booking confirmation/conversion), not per-request hot paths.

## No recursive self-proof
Verified in 3 places:
- `FieldOpsService._assert_tenant_customer_relationship`: the query never references the Job/Booking currently being created (it hasn't been persisted yet at check time).
- `Booking.convert_to_job`'s independent-evidence query explicitly excludes `Booking.id != b.id` (the Booking being converted).
- `FieldOpsService.create_job`'s direct `booking_id` path explicitly excludes `Booking.id != booking.id` and `Job.booking_id != str(booking.id)`.

No provider-created Booking can ever serve as its own evidence at any of the three authority-dependent decision points.
