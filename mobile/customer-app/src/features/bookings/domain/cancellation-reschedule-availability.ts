/**
 * CUSTOMER-L5-15 — single source of truth for whether this client may ever
 * offer an interactive cancel/reschedule action for a given booking.
 *
 * Both functions return `false` unconditionally. This is not a placeholder
 * awaiting wiring — it is the verified, correct answer for this backend as
 * it exists today. Exhaustive source tracing this sprint
 * (`CUSTOMER-L5-15-baseline-verification.md`, `contract-matrix.md`) found:
 *
 * - The real canonical booking pipeline (`final_records.ServiceBooking`/
 *   `ServiceJob`, created via `home_service_booking`'s confirm flow) has NO
 *   cancellation or reschedule mutation reachable by a customer anywhere in
 *   the backend — `final_records/customer_router.py` is read-only, and the
 *   only job-cancel endpoint (`execution/home_service_router.py`'s
 *   `provider_router.post("/{job_id}/cancel")`) is provider-role only.
 * - A separate, real, well-built cancellation/reschedule engine
 *   (`app/engines/booking/`, prefix `/v1/bookings`) does grant the
 *   "customer" role `P.BOOKING_CANCEL`/`P.BOOKING_RESCHEDULE` — but it
 *   resolves bookings against its own, disconnected `bookings` table
 *   (`Booking` model), which the real booking pipeline never writes to.
 *   Calling it with a real `ServiceBooking.id` returns 404
 *   `BOOKING_NOT_FOUND` every time — confirmed by tracing
 *   `HomeServiceFinalCreationService.finalize()` (the only real booking
 *   creation path) and finding zero references to `app.engines.booking`.
 *
 * Wiring the client to that engine would compile and look correct while
 * being guaranteed to fail against any real booking — this function exists
 * so `BookingDetailScreen` (and any future screen) has one place to flip
 * once the backend gap closes, rather than a scattered `false` literal, and
 * so this honest state is unit-tested and cannot silently regress into a
 * fake feature.
 */
export function isCancellationAvailable(_bookingStatus: string): boolean {
  return false;
}

export function isRescheduleAvailable(_bookingStatus: string): boolean {
  return false;
}
