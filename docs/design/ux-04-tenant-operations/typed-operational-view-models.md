# Typed Operational View Models

All 15 required view models are defined in
`frontend/tenant-portal/lib/ux04/types.ts`:
`BookingListItemView`, `BookingDetailView`, `JobListItemView`,
`JobDetailView`, `AssignmentCandidateView`, `QuoteView`, `ChecklistView`,
`PartsRequestView`, `InvoiceView`, `CreditCommissionView`,
`ComplaintDetailView` (brief's `ComplaintView`), `ComplianceSubmissionView`,
`OperationalActivityView` — modeled as reused `AuditEventFixture[]` fields
rather than a new wrapper type (no new shape was needed), `SLAStateView`,
`ReadinessStateView` — modeled as reused `ReadinessState` (UX-03) plus
`OperationalViewMeta.readiness`, again no new wrapper type needed.

Every view model retains: source pipeline (`BookingFixture.pipeline` /
`ServiceJobFixture.pipeline`), canonical id (`.canonicalId`), backend
readiness (`OperationalViewMeta.readiness`), available actions
(`ActionPermissionView[]`), permission presentation (`ActionPermissionView.
reason`), and source adapter (`OperationalViewMeta.sourceAdapter`).

Realistic fixtures for every model live in `lib/ux04/fixtures.ts` — no
lorem ipsum; names, addresses, amounts, and status values are concrete and
internally consistent (e.g. `jobDetailFixture` composes `quoteFixture`,
`checklistFixture`, `partsRequestFixture` etc. rather than being
independently invented).
