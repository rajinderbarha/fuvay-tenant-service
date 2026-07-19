# ServiceBooking Provenance Test Report

`lib/ux04/__tests__/provenance.test.ts` — 5 tests, all passing (see
`automated-test-report.md` for the full-suite run this appears in):

1. ServiceBooking id and ServiceJob id are both present and never equal.
2. `sourceModel`/`resultingModel` are always their fixed literal values —
   never substituted.
3. Pipeline labels (`booking_field_ops` vs
   `service_booking_service_job`) stay distinct between the field_ops.Job
   and ServiceJob fixtures used elsewhere in the showcase.
4. `serviceJobOnlySections` (quote/checklist/partsRequests/invoice/
   creditCommission) are declared explicitly in the provenance fixture and
   structurally proven absent as top-level keys on
   `FieldOpsJobDetailView`'s actual fixture object — not just documented,
   checked via `Object.keys()`.
5. `BookingFixture` rows (`bookingListFixture`) never carry a
   `sourceBookingId`/`resultingServiceJobId` key — Booking/field_ops.Job
   never receives ServiceBooking metadata.

Additionally, `components/ux04/__tests__/FieldOpsJobDetail.test.tsx`
structurally proves (via rendered heading text, not just type-level) that
the field_ops.Job detail page never renders a Quote/Checklist/Parts
requests/Invoice/Credit section heading.
