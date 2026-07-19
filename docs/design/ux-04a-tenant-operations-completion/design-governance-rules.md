# Design Governance Rules (UX-04A)

Same rules as UX-04 baseline, re-verified this pass:
- No raw hex colors in any of the 7 new components (grep-confirmed, see
  `theme-runtime-report.md`).
- No new status registry — `StatusBadge` reused unmodified.
- Canonical roles only — `staff-home` route explicitly uses the canonical
  `staff` role, no `dispatcher`/`manager` alias introduced anywhere in
  fixtures, types, or component code this pass (grep-confirmed: no match
  for those strings in any new file).
- Pipeline separation enforced at the type level — `PipelineAwareBookingDetail`
  branches on `booking.pipeline` and never converts a `BookingFixture`
  field into a `ServiceJobFixture` field or vice versa.
- PartsRequest ServiceJob-only, no technician install authority — both
  re-asserted as executable tests this pass
  (`PartsRequestSummary.test.tsx`), not just doc claims.
- Backward-compatible design-system changes only, documented — none made
  this pass; baseline's 2 fixes preserved unchanged.
