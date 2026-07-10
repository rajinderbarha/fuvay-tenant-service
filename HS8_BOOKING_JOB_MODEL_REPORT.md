# HS8 — Booking-to-Job Model Report

## Result: booking and job are separate but tightly linked real records

`HomeServiceFinalCreationService.finalize()` (HS7) creates both a
`ServiceBooking` and a `ServiceJob` atomically at booking confirmation
time — the job is not a later, separate creation step. `ServiceJob` has
its own `id`, `job_number`, `booking_id` FK, `tenant_id`, `assigned_staff_id`,
`status`, `scheduled_date`/`scheduled_time_window`, `city`/`zipcode`/
`address_snapshot`.

Live-verified: both real HS7 bookings (`BK-...-000001`, `BK-...-000002`)
have a corresponding real job (`JOB-...-000001`, `JOB-...-000002`),
`status: pending_assignment`, `assigned_staff_id: null`, tenant-scoped
correctly to the selected provider.

## Verdict
Booking-to-job conversion: **works correctly and automatically** — no
separate "convert booking to job" step exists or is needed.
