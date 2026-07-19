# Backend Contract Blockers (UX-04B)

Unchanged from UX-04A — no new view model this pass required a genuinely
new backend contract category. `SourceBookingReference`/`JobProvenance`
and `FieldOpsJobDetailView`/`PartsRequestListItemView` are all built from
existing UX-03 fixture types (`BookingFixture`, `PartsRequestFixture`),
not new backend-dependent shapes. The provisional ServiceBooking id
(`servicebooking-provenance-contract.md`) is a real backend-contract gap
carried forward, not newly created.
