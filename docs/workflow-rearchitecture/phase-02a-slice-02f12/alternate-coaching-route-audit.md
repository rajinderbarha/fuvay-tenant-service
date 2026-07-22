# Alternate Coaching Route Audit — Slice 2F-12 (Workstream 14)

**This is an audit and classification only, per the mission's explicit
prohibition on implementing `app.engines.coaching_appointment` as a new
workstream.**

## Mounted
Yes — `app/main.py` mounts
`app.engines.coaching_appointment.customer_router` and
`app.engines.coaching_appointment.admin_router`.

## Models
`CoachingAppointmentDraft`, `CoachingAppointmentDraftEvent`,
`CoachingAppointmentSlotHold` — the pre-confirmation draft/slot-selection
flow (find centers, available slots, select slot, fee estimate, confirm,
cancel-draft), distinct from `CoachingAppointment` (the confirmed,
post-conversion record `execution.coaching_router` operates on).

## Relationship to `execution.coaching_router`
**Distinct model, distinct table, distinct lifecycle stage** —
identical relationship to real estate's `execution.real_estate_router`
↔ `real_estate_lead` split (Slice 2F-11A). `CoachingAppointment.draft_id`
is the only structural link. No route in `coaching_appointment.customer_router`
or `admin_router` reads or mutates `CoachingAppointment` directly —
confirmed by grep (no `CoachingAppointment` import in either file, only
`CoachingAppointmentDraft`/`CoachingAppointmentSlotHold`).

## Capability overlap classification
**DISTINCT_MODEL_DISTINCT_CAPABILITY** — `coaching_appointment` handles
pre-confirmation slot selection and booking; no route performs the
post-confirmation appointment-execution lifecycle
(accept/reject/start/complete/no-show/reschedule/cancel) that
`execution.coaching_router` implements.

## Authorization pattern (documented, not modified)
`coaching_appointment.customer_router` uses standard
`Depends(get_current_user)` for authentication (unlike
`real_estate_lead.customer_router`'s unusual inline-call pattern) —
confirmed by direct source read. This module's own authorization
strength was not otherwise independently re-audited this slice (out of
scope). Its own test suite (`tests/test_sprint17_coaching_appointment.py`,
46 tests) is live and passing, re-run this slice with no failures,
supporting the classification that this is a distinct, functioning
module, not a disconnected scaffold.

## Admin router
Not independently re-verified for its own guard strength this slice
(out of scope — no capability overlap with the security boundary this
slice closed).

## Final disposition
`DISTINCT_MODEL_DISTINCT_CAPABILITY` — no weaker overlapping live route
exists, because no overlapping capability exists at all. `REQUIRES_FUTURE_DEDICATED_SLICE`
if `coaching_appointment`'s own authorization is ever to be independently
hardened — explicitly out of scope here.
