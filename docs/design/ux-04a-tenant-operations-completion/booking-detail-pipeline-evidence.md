# Booking Detail Pipeline Evidence

`PipelineAwareBookingDetail` (`components/ux04/PipelineAwareBookingDetail.tsx`)
accepts `BookingFixture | ServiceJobFixture` and switches its rendered
fields — never converted values — based on `booking.pipeline`:

- `pipeline === "booking_field_ops"`: renders `assignedStaffId` only.
- `pipeline === "service_booking_service_job"`: renders
  `assignedTechnicianId` and an explicit note that job-specific sections
  (quote/checklist/parts/invoice/credit) are intentionally withheld from
  this view.

**Caveat, stated honestly**: UX-03's fixture layer
(`lib/ux03/types.ts`/`fixtures.ts`) never modeled a distinct
"ServiceBooking" pre-job fixture type separate from `ServiceJobFixture` —
per UX-03's own `booking-job-pipeline-separation.md`, the ServiceBooking ->
ServiceJob pipeline is represented end-to-end by `ServiceJobFixture`. This
pass's "Booking Detail — ServiceBooking pipeline" therefore renders the
same `ServiceJobFixture` used elsewhere for the Job Detail Workspace, just
with job-specific sections hidden — it is not a genuinely separate
pre-transition entity. Building a real distinct ServiceBooking type would
require either a UX-03 type change (out of this phase's stated scope,
since it's a different phase's committed foundation) or a confirmed
backend contract showing ServiceBooking has fields distinct from
ServiceJob pre-transition. Recorded as a `PRODUCT_DECISION_REQUIRED` item.
