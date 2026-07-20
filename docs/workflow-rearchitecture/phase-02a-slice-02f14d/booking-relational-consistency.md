# Booking Relational Consistency

## Disposition: BOOKING_FIELDS_CROSS_CHECKED

## Verified / fixed this slice

- **Booking belongs to principal tenant**: enforced (Slice 2F-14C, unmodified).
- **Booking uses the exact expected booking model**: `app.engines.booking.models.Booking` —
  confirmed the same model `Booking.convert_to_job` itself uses (no distinct/duplicate booking
  model exists).
- **Booking customer matches the new Job customer**: fixed this slice
  (`CUSTOMER_BOOKING_MISMATCH` if an explicitly-supplied `customer_id` disagrees with
  `booking.customer_id`).
- **Booking service matches the new Job service_type**: fixed this slice
  (`SERVICE_BOOKING_MISMATCH` if an explicitly-supplied `service_type_id` disagrees with
  `booking.service_type_id`).
- **Booking status permits Job creation**: **not enforced** by `create_job` — `Booking.status`
  (e.g. requiring `BS.CONFIRMED`, as `Booking.convert_to_job` requires) is never checked here.
  This is disclosed as a gap, not silently assumed safe — see known-limitations.md. Given
  `create_job`'s `booking_id` is a manual reference field (not the atomic conversion path), and
  no evidence exists that any caller relies on a status precondition for this field, closing it
  would require inventing new product policy about which booking statuses are valid for a manual
  reference-only link. Recorded as `PRODUCT_DECISION_REQUIRED`, not fixed.
- **Booking has not already produced a Job where uniqueness is expected**: fixed this slice —
  mirrors `Booking.convert_to_job`'s own `converted_job_id` check plus an explicit
  `Job.booking_id == booking_id` existence query.
- **Booking tenant/customer/service cannot be overridden**: fixed this slice (mismatches
  rejected, not silently overridden — the request is rejected rather than the booking's values
  silently winning, since `create_job` is a manual endpoint and silently discarding a client's
  explicit customer_id/service_type_id would be a worse surprise than a clear 422).
- **Booking and parent_job_id compatibility**: not enforced as mutually exclusive — see
  supported-creation-modes.md's "Ambiguous mixtures" section.
- **No ServiceBooking adapter introduced**: confirmed — all checks use the existing `Booking`
  model directly, no new cross-pipeline code was added.

## Not BOOKING_FIELDS_AUTHORITATIVE

`create_job` does **not** auto-derive `customer_id`/`service_type_id` from the booking when they
are omitted from the request — it only rejects a mismatch when both are explicitly supplied. This
is a deliberate, minimal-scope choice: auto-filling omitted fields from the booking would be new
product behavior (effectively re-implementing part of `Booking.convert_to_job`'s derivation logic
inside a different, generic endpoint) rather than a closure of a proven inconsistency defect.
