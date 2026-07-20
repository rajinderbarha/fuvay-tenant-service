# Direct field_ops Reference Safety

## The bypass this closes
`Booking.convert_to_job` is the intended, canonical conversion pipeline. But `field_ops.router`'s own generic `create_job` endpoint independently accepts an optional `booking_id` field, referencing the Booking's customer/service data directly, without going through `convert_to_job` at all. Prior to this slice, this meant `convert_to_job`'s new independent-relationship-proof requirement (see `booking-conversion-legacy-safety.md`) could be trivially bypassed by calling `create_job` with `booking_id` set instead.

## The fix
`FieldOpsService.create_job`'s `booking_id` validation block now applies the IDENTICAL check: read the referenced Booking's creation-history row; if not customer-originated, require independent relationship evidence (excluding the referenced booking itself); if absent, raise `CUSTOMER_TENANT_RELATIONSHIP_REQUIRED` (422) before any persistence.

This is inserted after the existing duplicate-Job-for-booking guard (Slice 2F-14D) and before the final `customer_id` validation block, so it runs for every `booking_id`-referencing `create_job` call regardless of whether `customer_id` is also separately supplied.

## Result
Both entry points into "a Booking becomes a Job" (`convert_to_job` and `create_job` with `booking_id`) now enforce the same provenance rule — there is no remaining path to convert an untrusted, provider-created Booking into a Job without independent relationship evidence.
