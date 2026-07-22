# Enrolment/Conversion Integrity — Slice 2F-12 (Workstream 10)

## UNSUPPORTED_CAPABILITY in this router — reported honestly, not fabricated
No enrolment, programme/batch assignment, or lead/hold-to-appointment
conversion route exists anywhere in `execution.coaching_router`. The
appointment reaching this router is already confirmed (converted from a
draft) before any route here is invoked — the conversion itself (draft →
`CoachingAppointment`) happens in a different module
(`app.engines.coaching_appointment`, out of scope — see
`alternate-coaching-route-audit.md`).

## Conclusion
Every requirement in this workstream (duplicate target prevention,
converted-flag/target-persistence consistency, financial effects of
conversion) is vacuously satisfied for `execution.coaching_router`
specifically, since this router performs no conversion of any kind.
