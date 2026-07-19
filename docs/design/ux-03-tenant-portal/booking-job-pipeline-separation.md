# Booking / Job Pipeline Separation

Two genuinely separate pipelines exist and must never be merged in the UI:

1. **Booking pipeline**: `Booking` -> `field_ops.Job`. Represented by
   `BookingFixture` (`pipeline: "booking_field_ops"`, `canonicalId` = the
   `field_ops.Job` id).
2. **Service Job pipeline**: `ServiceBooking` -> `ServiceJob`. Represented
   by `ServiceJobFixture` (`pipeline: "service_booking_service_job"`,
   `canonicalId` = the `ServiceJob` id).

Every list row and detail page for either pipeline renders a
`PipelineBadge` (`components/ux03/widgets/PipelineBadge.tsx`) showing which
pipeline the row belongs to and its canonical backend id, so the two are
never silently collapsed into one generic "job/booking" concept.

`PartsRequest` belongs only to the `ServiceJob` pipeline — there is no
`PartsRequest` concept on a `field_ops.Job`. The Job Detail dev-showcase
page's "Parts" section and the dedicated Parts Approval showcase both only
ever reference `ServiceJobFixture.partsRequestIds`.

Customer cancellation/rescheduling is UNRESOLVED product-side for both
pipelines. Both fixture types type this as
`cancelSupported: "unresolved_mock_only"` and no showcase page renders a
working cancel/reschedule action — `permissions-and-pipelines.test.ts`
asserts this field's value on every fixture row.
