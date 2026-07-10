# HS8 — Customer Tracking Report

## Result: updates correctly, live-verified

`HomeServiceJobExecutionService._set_status()` calls
`self.sync_booking_status(db, job.booking_id, new_status)` on every
transition — the linked `ServiceBooking.status` is kept in sync with the
job's execution status in real time.

Live-verified: after driving job `JOB-20260709-000001` through
`accept → on_the_way → reached_site → inspection_started →
inspection_done → service_started → work_done`, calling
`GET /v1/customer/bookings/{booking_id}` (as `customer@serviceos.in`)
returned `status: "work_done"` and `job_status: "work_done"` — reflecting
the real, current state, not stale data. `payment_mode`,
`selected_price_option`, `selected_price_amount` (all from HS7)
remained intact and correct throughout.

## Gap found (not fixed — documented)
`GET /v1/customer/bookings/{booking_id}/tracking`'s timeline is built
only from `ServiceJobAssignmentEvent` rows (assignment-created,
technician-accepted, etc.) — it does **not** include the execution
engine's own richer event stream (`on-the-way`, `reached-site`,
`work-done`, etc. from `ServiceJobExecutionEvent`). So while the
top-level `status` field is accurate and live, the customer-facing
timeline itself under-reports the real granularity of what happened.
Not fixed this pass (would require merging two separate event streams
with a shared customer-safe label map) — a real, honest gap.

## Verdict
Customer tracking: **status updates correctly and is live-verified
accurate.** Timeline granularity is a documented, non-blocking gap. Not
`NOT_READY_HS8_CUSTOMER_TRACKING_FAILED`.
