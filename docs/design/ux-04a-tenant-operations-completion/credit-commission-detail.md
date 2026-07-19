# Credit / Commission Detail (UX-04A)

No change to `CreditCommissionSummary`/`CreditCommissionView` this pass —
still MERGED_WITH_NAMED_WORKFLOW into Job Detail Workspace (item 17).
`CreditCommissionSummary.test.tsx` (new this pass) asserts no
payout/withdrawal button renders and the "not customer money"/"not a
payout" footer copy is present — codifying the credit/commission/deposit/
payment separation as a test, not just a doc claim.
