# Coaching Model Lineage — Slice 2F-12 (Workstream 2)

## Models actually present in `execution.coaching_router`'s reach

| Model | Table | Classification |
|---|---|---|
| `CoachingAppointment` | `coaching_appointments` | CONSULTATION_OR_COUNSELLING (a confirmed, already-booked appointment; the model's own docstring: "Final coaching appointment created from a confirmed draft") |
| `CoachingAppointmentExecutionEvent` | (execution events table) | AUDIT_OR_HISTORY — one row per status transition |
| `CoachingAppointmentNote` | (notes table) | CUSTOMER_SELF_SERVICE_RECORD-adjacent (a sub-record of the appointment) — `is_customer_visible` flag distinguishes internal vs customer-visible |

`CoachingAppointment` carries direct student contact fields
(`student_name`, `student_phone`, `student_email`), requirement fields
(`target_exam`, `target_band`, `preferred_mode`), and scheduling fields
(`selected_date`, `selected_time_start/end`, `city`) — captured at
draft-confirmation time, not mutated by any route in this router.

## Models NOT present in this router (confirmed absent, not assumed)
No slot, slot-hold, capacity, enrolment, conversion-flag, batch, course,
or programme model exists anywhere in `execution.coaching_router`'s
reach. Every workstream targeting those capabilities (8, 10, 11, 19) is
reported as `UNSUPPORTED_CAPABILITY` in this router — see
`slot-hold-integrity.md` and `enrolment-conversion-integrity.md`.

## Where that machinery actually lives
`app.engines.coaching_appointment` (a distinct module) has
`CoachingAppointmentDraft`, `CoachingAppointmentDraftEvent`, and
`CoachingAppointmentSlotHold` — the pre-confirmation slot-selection and
booking flow. `CoachingAppointment.draft_id` is the only structural link
(a foreign key on the *execution*-stage model, confirming a draft was
converted into this confirmed appointment at some point outside this
router's reach). See `alternate-coaching-route-audit.md` for the full
classification of that module.

## No models were merged
Per the mission's explicit instruction, `CoachingAppointment` was not
merged with `CoachingAppointmentDraft`/`CoachingAppointmentSlotHold`, nor
with Booking/Job/ServiceBooking/ServiceJob. No adapter was created
between these record types.
