# Parts Request Tracking (technician, read-only)

`PartsRequestStatusCard` (built in the previous session's pass) renders `PartsRequestStatusView` --
`requested/under_review/approved/rejected/installed`, color-coded, with `providerResponse` shown when present.
`technicianActions` is typed to only ever contain `"add_note"` (compile-time-guarded, see
`src/types/__tests__/provenance.test.ts`) -- no approve/reject/mark-installed/link-to-field_ops/create-supplier-
order affordance exists in the type, so no screen built on top of it can accidentally expose one.

`PartsRequestShowcaseScreen` (previous session) already demonstrates both creation and tracking together against
local fixture state. This session did not add a *separate* tracking-only screen since the showcase already
covers the tracking list rendering; it was not wired into the real `JobDetailScreen` job-detail flow this pass
(would need a real parts-request-list-by-job endpoint, which doesn't exist -- see `backend-contract-blockers.md`).
