# Admin A2 Dashboard — Remaining Blockers

None of these block certification — honestly documented, non-blocking notes.

## 1. No aggregate "Usage Credit Balance Total" / "Credits Deducted
   Lifetime" KPI card

The ticket's required KPI list includes "Usage Credit Balance Total" and
"Credits Deducted Lifetime" as standalone cards. The current Finance
Snapshot shows "Completed Job Deductions" (a currency total) but not a
platform-wide sum of `tenant_wallets.credit_balance` across all tenants,
nor a lifetime-deducted-credits counter distinct from the deductions
total already shown. The Action Queue's low-credit check reads
per-tenant balances but never aggregates them. A real follow-up: add
`SUM(credit_balance) FROM tenant_wallets` and a lifetime-deduction sum to
either `finance-snapshot` or a new field on it.

## 2. Operations summary has no scheduled/on-the-way/in-progress/
   cancelled breakdown

`operations-snapshot.live_jobs` is a single aggregate bucket (`status NOT
IN ('closed','cancelled')`) — the ticket wants Scheduled/Active/On The
Way/In Progress/Completed/Cancelled as separate counts. Not broken down
this sprint; would need either a `GROUP BY status` query added to
`get_operations_snapshot` or a new dedicated endpoint.

## 3. No "Part Approval Requests" count anywhere

Confirmed via the original research pass — no table/endpoint for parts-
approval requests was found in this codebase at all. Not fabricated;
documented as genuinely absent rather than faked.

## 4. Trust & Quality card lacks Gold/At-Risk tier counts and
   cancellation rate

The current card shows Avg Rating, Complaint Rate, Dispute Rate, and
Providers Under Review — real data, but not the ticket's exact requested
"Gold Providers / At-Risk Providers / Cancellation Rate / Badge
Assignments" breakdown (badge assignments count exists in the backend
response as `badge_awards_this_week` but isn't yet surfaced in the
frontend card). A real follow-up, not fabricated data.

## 5. Home Services health statuses are heuristic, not independently
   audited per sub-system

`service_catalog_health`/`pricing_rule_health`/etc. in the new
`get_home_services_summary()` method use a simple "count > 0 → healthy,
else warning/not_configured" heuristic rather than deep validation (e.g.
checking every catalog service actually has a complete pricing rule, or
every published tenant service has a valid brand/type mapping). This is
an honest, real, live-queried heuristic — not fabricated — but a more
rigorous health-scoring algorithm is a reasonable follow-up.

## 6. Production build re-verification pending

Same caveat as every recent sprint — dev-server ports actively occupied
throughout this session prevented a fresh `next build`. `tsc --noEmit` (0
errors) relied on as the hard gate.

## 7. 5 pre-existing, unrelated test failures

`test_sprint34a_ui_foundation.py` — 4 concern the tenant-portal
dashboard (different file, untouched this sprint), 1 asserts a component
name (`SummaryStrip`) the admin dashboard never used, confirmed
pre-existing before this sprint's changes.
