# Test Report — Slice 2F-14B

## New tests

`tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` — 21 tests, all
passing:

- `TestCreateJobTenantPinning` (2) — tenant_owner cannot override tenant_id; super_admin's
  explicit tenant_id is preserved.
- `TestSpawnRepairOwnership` (3) — cross-tenant denied, duplicate spawn rejected, wrong job_type
  rejected.
- `TestCreateQuoteOwnership` (3) — foreign job, cross-tenant, unassigned technician all denied.
- `TestQuoteManagementDeniesCustomer` (3) — customer denied from `create_job_quote`/
  `create_quote`; tenant_owner can create a quote.
- `TestRespondToQuoteIdentity` (4) — correct customer succeeds, foreign customer denied
  (quote unchanged), repeated response rejected, foreign quote ID rejected.
- `TestRouterGuardSources` (6) — source-level verification that every router dependency upgrade
  is actually wired (not just intended).

All fixtures are deterministic (`MagicMock`/`AsyncMock` job/quote/db objects with explicit
attribute values and explicit `side_effect` sequencing for multi-query methods) — behavior is
proven by direct service-method invocation, not source-string assertion alone (only
`TestRouterGuardSources` uses source inspection, to confirm wiring, not behavior).

## Regression

See regression-report.md — 1264 passed in the broad partition sweep; 15 pre-existing
live-environment exclusions honestly separated out and not counted as passing.
