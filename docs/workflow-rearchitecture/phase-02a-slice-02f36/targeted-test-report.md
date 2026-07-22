# Targeted Test Report

`tests/test_phase2f36_enterprise_tenant_admin_operational_batch.py` — 40
tests across 9 classes:

- `TestScopeGuardsLive` (1) — all 42 routes access-scope gated, live
- `TestTrustedTenantHelpers` (16) — presence + super-admin-exempt/tenant-
  match/tenant-mismatch/missing-context behavior for all 8 touched
  services
- `TestChatParticipantCheck` (3) — customer membership positive/negative,
  staff bypass
- `TestAppointmentOwnership` (5) — same-tenant/foreign-tenant/customer-
  own/customer-foreign/super-admin
- `TestEnterpriseGridSetDefaultOwnership` (1)
- `TestNoBypassOfClosedRoutes` (1) — direct-service-call bypass audit
- `TestSetBAdjudication` (4) — full adjudication count, canonical-
  protection count, bookings exclude, read-only excludes
- `TestCanonicalClosure` (5) — coverage arithmetic, Set A/B protection
- `TestM01N01GeoAnd2F35NonRegression` (4)

**Result: 40/40 passed.**

Every positive assertion has a paired negative control (tenant mismatch
rejected, foreign object non-oracular, missing context rejected, staff
vs customer role divergence).
