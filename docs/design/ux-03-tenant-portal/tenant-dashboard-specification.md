# Tenant Dashboard Specification

One configurable dashboard, two variants selected by
`TenantProfileFixture.reviewState`:
- **Pre-approval** (`/dev/ux-03/dashboard-pre-approval`): profile
  completion %, document status, package/deposit readiness, review status
  banner.
- **Approved** (`/dev/ux-03/dashboard-approved`): business snapshot, action
  center (pending parts/complaints), operations overview (job-status
  counts; a recharts widget is noted but not implemented as a live chart
  this phase — see dashboard-widget-inventory.csv), finance overview
  (credit/commission/deposit shown separately), business health, recent
  activity.

Both variants reuse `ReviewStateBanner` and `Card`/`PageHeader` from the
design system — not two unrelated page implementations.
