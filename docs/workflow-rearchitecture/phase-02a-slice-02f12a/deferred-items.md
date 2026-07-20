# Deferred Items — Slice 2F-12A

Explicitly deferred, per the out-of-scope list — none investigated,
designed, or acted on:

1. `field_ops.checklist_router`, `field_ops.staff_router` — not begun.
2. `app.engines.coaching_appointment` — not modified (its draft-cancel
   was classified as a distinct-model capability for the alternate-route
   audit only).
3. No coaching slot holds, enrolment, or course workflows were built.
4. No coach/counsellor/instructor/manager role or permission alias was
   created; no new permission was added.
5. Appointment statuses and `APPT_TRANSITIONS` were not changed.
6. No cancellation-fee or refund workflow was built.
7. No notification infrastructure was built.
8. No coaching frontend was built; no visual redesign occurred.
9. `CoachingAppointment` was not merged with Booking/ServiceBooking/Job/
   ServiceJob.
10. Booking Exception Resolution, Admin/Tenant My Work, Next-Action
    aggregation were not implemented.
11. `readonly@demo-ac-services.local` was not remediated; migration 144
    was not applied.
