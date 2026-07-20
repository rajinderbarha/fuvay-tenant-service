# Alternate Route Audit

Searched for any other route or service method that could construct, confirm, or convert a Booking, or create a field_ops.Job from one, outside the 11 mounted `booking.router` routes and `FieldOpsService.create_job`/`convert_to_repair`/`spawn_repair`:

- `app.engines.provider_portal.router::update_booking_window` — manages tenant booking *availability windows* (capacity/slots), not Booking rows themselves. Unrelated model. Already `TENANT_MUTATION_ROLE_SCOPE_AWARE` (Slice 2F-2), out of scope.
- `app.engines.serviceability` — matches tenants to a location for booking *preflight*, does not create/confirm/convert Bookings. Confirmed no persistence.
- No other router or service method references `Booking.convert_to_job`, `BookingService.create_booking`, `BookingService.confirm_booking`, or writes to the `bookings` table directly.
- `FieldOpsService.create_job`, `.convert_to_repair`, `.spawn_repair` were previously audited (2F-14 series); `convert_to_repair`/`spawn_repair` operate on `field_ops.Job` parent/child lineage only, not on `Booking` rows, so the Booking-provenance fix does not apply to them (already correctly scoped by the existing `parent_job_id` path in `create_job`, which this slice's audit re-confirmed is unaffected).

No additional mutation path into Booking/Job creation-via-Booking was found.
