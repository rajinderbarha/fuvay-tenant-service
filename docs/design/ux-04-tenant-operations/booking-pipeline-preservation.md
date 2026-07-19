# Booking Pipeline Preservation

Same hard rule as UX-03's `booking-job-pipeline-separation.md`, restated
for UX-04's new view-model layer: `BookingListItemView`,
`BookingDetailView`, and `BookingToJobTransitionView` all wrap
`BookingFixture` (`pipeline: "booking_field_ops"`, `canonicalId` = the
`field_ops.Job` id) directly and never coerce it into the `ServiceJob`
shape. `JobListItemView`/`JobDetailView` wrap `ServiceJobFixture`
(`pipeline: "service_booking_service_job"`) the same way. No UX-04 type or
component accepts a union of the two fixture types — each view model is
pipeline-specific by construction, so a type error (not a runtime check)
would catch an accidental merge attempt.
