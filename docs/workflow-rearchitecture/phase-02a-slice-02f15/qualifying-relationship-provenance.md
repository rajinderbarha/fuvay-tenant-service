# Qualifying Relationship Provenance (Post Booking-Engine Closure)

## Disposition: EXISTING_RELATIONSHIP_ASSISTED_BOOKING + CUSTOMER_ORIGINATED_BOOKING (both now trustworthy)

With this slice's fix, EVERY Booking that can reach `QUALIFYING_BOOKING_STATUSES` now has
trustworthy provenance by construction:

- **`CUSTOMER_ORIGINATED_BOOKING`**: created via customer self-booking — customer identity was
  server-derived at creation; the customer's own act of creating it is their consent. Reaching
  `CONFIRMED` adds the tenant's acceptance. **Trustworthy.**
- **`EXISTING_RELATIONSHIP_ASSISTED_BOOKING`**: created via the tenant-assisted path — as of this
  slice, this path can ONLY succeed if a qualifying relationship (a Booking or Job) ALREADY
  existed for that (tenant, customer) pair before this new Booking was created. **Trustworthy by
  induction**: the new Booking's own qualification is backed by a prior qualifying record, which
  itself was either customer-originated or backed by a still-earlier qualifying record — the
  chain must bottom out at a customer-originated record, since assisted-booking creation without
  any prior evidence is now rejected (`CUSTOMER_TENANT_RELATIONSHIP_REQUIRED`).

## `PROVIDER_ONLY_BOOKING_NON_QUALIFYING` — no longer a live category

Before this slice, a "provider-only" Booking (created without any prior relationship, for an
arbitrary customer) could reach `CONFIRMED` and would then have qualified — this WAS the
vulnerability. After this slice's fix, such a Booking can no longer be CREATED at all, so
`PROVIDER_ONLY_BOOKING_NON_QUALIFYING` bookings simply do not exist in the live system going
forward (existing legacy rows, if any, are addressed below).

## Legacy bookings created before this slice's fix

Any `Booking` row created before this slice's deployment, by the (now-closed) unvalidated
tenant-assisted path, could theoretically still be sitting in `CONFIRMED`-or-later status in the
database with no genuine prior relationship. This slice's fix only prevents NEW such Bookings
from being created — it does not retroactively audit or invalidate pre-existing rows. This is
disclosed honestly as a known limitation (see known-limitations.md) rather than silently ignored;
no migration or data audit was performed (out of scope — "a new database field or migration is
not automatically permitted," and no evidence-based way exists to distinguish these historical
rows from legitimate ones without inventing a marker).

## No change to `_assert_tenant_customer_relationship` itself

Confirmed: this slice made zero changes to `FieldOpsService._assert_tenant_customer_relationship`
(Slice 2F-14G's own predicate) — the fix is entirely upstream, in `BookingService.create_booking`.
This matches the mission's explicit instruction not to reopen field_ops relationship logic unless
proven necessary; it was not necessary.
