# Pipeline Provenance Report — UX-06 Round 4

Confirmed via source (`app/engines/final_records/confirm_router.py`): the
canonical confirm endpoint's success response explicitly returns
`{record_type: "booking", booking_id, booking_number, job_id, job_number,
status}` — both the `ServiceBooking` (booking_id/booking_number) and the
`ServiceJob` (job_id/job_number) references are present and distinct, never
merged into a single ID field. `src/lib/api.ts::BookingConfirmationResult`
mirrors this exactly. This is the ServiceBooking→ServiceJob pipeline,
consistent with UX-04's pipeline-separation rule.

Separately, `fieldOpsJobsApi` (Round 2) covers the OTHER pipeline
(Booking→field_ops.Job, `/v1/customer/jobs*`) — confirmed still distinct, not
touched or conflated by this round's work.

No booking was actually created this round (see booking-submission-live-evidence.md),
so `BookingDetailScreen`'s actual rendering of both provenance fields together
could not be visually verified — this is a real, undischarged item, not
assumed complete.
