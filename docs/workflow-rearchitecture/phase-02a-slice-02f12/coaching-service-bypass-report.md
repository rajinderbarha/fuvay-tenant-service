# Coaching Service Bypass Report — Slice 2F-12 (Workstream 15)

## Every method reached by `coaching_router`, and every caller
Confirmed via full-repository grep that `coaching_router.py` is the
**only** caller of `CoachingAppointmentExecutionService`'s methods
(`accept_appointment`, `reject_appointment`, `start_appointment`,
`complete_appointment`, `mark_no_show`, `request_reschedule`,
`cancel_appointment`, `add_note`, `get_timeline`, `get_notes`) —
excluding test files.

## No bypass found
Every one of these methods already correctly:
- Filters by `tenant_id` in `_get_appt`.
- Enforces `_assert_staff_owns_appt` for 7 of the 8 mutations
  (`cancel_appointment` intentionally does not — documented, not a
  bypass, since the persona layer already requires an authorized
  tenant-wide office role).
- Validates `APPT_TRANSITIONS` before mutating (`_assert_transition`
  runs before `appt.status = new_status`).

The only gap was the **router-level persona check**, now fixed. No
directly-connected service-layer bypass was found — the service layer's
ownership logic was already complete.

## No repository-wide coaching coverage is claimed
This report covers only `CoachingAppointmentExecutionService`. The
separate `app.engines.coaching_appointment` module (draft/slot-selection)
was not independently re-audited service-layer-by-service-layer this
slice — out of scope.
