# Independent Relationship Proof

## Requirement
When a Booking being converted (`Booking.convert_to_job`) or directly referenced (`FieldOpsService.create_job` with `booking_id`) was NOT customer-originated (its creation-history row's `changed_by_role != "customer"`), the action must be backed by relationship evidence INDEPENDENT of that same Booking — i.e. a *different* qualifying, customer-originated Booking for the same tenant+customer, or a source-derived field_ops.Job (one referencing a `booking_id`/`parent_job_id`) for the same tenant+customer, excluding the Booking/Job currently being acted on.

## Why "independent" and not just "any qualifying Booking"
Without excluding the Booking-in-question from its own evidence query, a provider-created Booking would trivially "prove" its own relationship (a booking always matches itself), defeating the entire point of the check. Excluding `Booking.id != <the booking being converted>` (and, for `create_job`, `Job.booking_id != <this booking>`) forces genuine independent evidence to exist.

## Where implemented
- `app/engines/booking/service.py::BookingService.convert_to_job` — added directly after the existing "no existing Job already references this booking" duplicate guard.
- `app/engines/field_ops/service.py::FieldOpsService.create_job` — added in the `booking_id` validation block, after the existing duplicate-Job-for-booking guard, before the standalone `customer_id` validation block.

## What happens when independent evidence is missing
`ServiceOSException("CUSTOMER_TENANT_RELATIONSHIP_REQUIRED", ..., status_code=422)` is raised before any persistence — `db.add` is never called (verified via `db.add.assert_not_called()` in the new test file's rejection-path tests).

## Interaction with a customer-originated Booking
If the Booking IS customer-originated, the independent-evidence sub-query never executes at all (short-circuited) — this is the normal, unaffected path for the overwhelming majority of real bookings.
