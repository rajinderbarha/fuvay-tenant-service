# Duplicate/Concurrency Review — Slice 2F-12 (Workstream 11)

## Repeated mutation calls
Every mutation's target status is validated against `APPT_TRANSITIONS`
before any change — a repeated call after a status has already advanced
past its legal source state is rejected (`STATE_TRANSITION_REJECTED`),
not idempotent. Confirmed via the unmodified, pre-existing
`test_sprint21_execution.py::TestCoachingExecution` suite and this
slice's own `TestAssignmentOwnershipReVerified`.

## Repeated note creation
`add_note` has no idempotency guard and none was added — an ordinary
repeated note is a legitimate conversation/consultation-log entry, not a
duplicate mutation to reject (same established pattern as complaints and
real estate).

## No slot/hold/conversion concurrency concern in this router
Since no capacity, hold, or conversion capability exists in this router
(see `slot-hold-integrity.md`, `enrolment-conversion-integrity.md`),
there is no concurrency race to analyze for this module specifically.

## `cancel_appointment` and repeated cancellation
`cancelled` has an empty transition set — a second cancel attempt on an
already-cancelled appointment is rejected by `_assert_transition`
(`STATE_TRANSITION_REJECTED`), not a duplicate financial/record-creation
concern (no side effect beyond the status field and one audit event).
