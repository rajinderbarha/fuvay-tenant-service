# CUSTOMER-L5-12 — Booking–Job Contract

## Cardinality

**One booking → zero or one `ServiceJob`.** Confirmed by
`ServiceJob.booking_id`'s own index (`ix_sj_booking_id`, not unique in the
schema, but every real creation path — `HomeServiceFinalCreationService.finalize()`
— creates exactly one job per booking at confirmation time, and no code
path was found anywhere that creates a second job for the same booking).
There is no real multi-job-per-booking scenario in this backend today.

## Creation Timing

The job is created **atomically with** the booking, inside the same
`finalize()` transaction (CUSTOMER-L5-11's own conversion-contract.md) —
there is no real "booking exists, job created later" gap in practice for
a freshly confirmed booking. This sprint's `GET /v1/customer/bookings/{id}`
response therefore always includes `job_status`/`scheduled_date`/
`scheduled_time_window` for any booking created through the real flow —
the "no job yet" case this sprint's detail screen defensively handles
(falling back to `preferred_time_window` when `scheduled_time_window` is
absent) is a safety net for a state that should not occur through the
real creation path, not a commonly-observed real scenario.

## Current-Job Selection

Not applicable — since there is at most one job per booking, there is no
"select the current one among several" logic to build.

## Replacement or Reassignment

**Technician reassignment is real**, but it does not create a new
`ServiceJob` — it updates the *same* job's `assigned_staff_id`/`status`
and records a new `ServiceJobAssignment` row (with the prior one's
`is_current` presumably flipped to `false`, though this sprint's client
code never reads `ServiceJobAssignment` directly — only the derived
`assignment_status`/`assignment_message` on the booking/job, and the
`ServiceJobAssignmentEvent` timeline, which records an
`assignment_reassigned` event customer-safely as "Technician updated.").

## Cancelled Jobs

No real job-cancellation-while-keeping-booking-active scenario was found
reachable by any customer-facing path — `assignment_cancelled` (a real
event type) reflects a *provider-side* assignment cancellation (the
provider un-assigns a technician, reverting the job back to
`pending_assignment`), not a customer-visible "this job was cancelled and
replaced by a new one" scenario. This sprint's timeline renders
`assignment_cancelled` honestly (customer-safe label: "Provider is
finding a technician.") without implying the whole booking was cancelled.

## Customer Visibility

The customer never sees a raw `job_id` in this sprint's UI (the detail
endpoint inlines `job_status`/`scheduled_date`/`scheduled_time_window`
directly onto the booking response — no separate job object is exposed).
This is a deliberate, real backend design choice this client follows
exactly, not a gap.

## Cache Behavior

Both `useBookingDetail` and `useBookingTracking` are scoped by
`bookingId` (not `jobId`) — consistent with the customer never needing to
reference a job independently of its booking (`cache-policy.md`).

## Test Coverage

Covered implicitly via `booking-detail-schema.test.ts`'s "with a job" and
"without a job" cases — both real, valid response shapes this client's
schema accepts (job fields fully optional).
