# Job Model Preservation

`JobDetailView.job: ServiceJobFixture` is never widened to accept a
`BookingFixture`. `JobDetailView.partsRequests: PartsRequestView[]` only
ever references `PartsRequestFixture.serviceJobId` — there is no code path
in `lib/ux04/types.ts` or `components/ux04/PartsRequestSummary.tsx` that
can attach a parts request to a `field_ops.Job`. `commissionBps` lives on
`ServiceJobFixture` only (booking has no commission field), preserving the
credit/commission model's ServiceJob-only scope end to end.
