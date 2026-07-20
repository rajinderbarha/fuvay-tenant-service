# Targeted Test Report

`tests/test_phase2f37_financial_product_policy_batch.py` — 27 tests
across 9 classes:

- `TestScopeGuardsLive` (1) — all 19 routes access-scope gated, live
- `TestTrustedTenantHelpers` (6) — presence + super-admin-exempt/tenant-
  match/tenant-mismatch/missing-context behavior for all 3 touched
  services
- `TestPricingZoneRuleOwnership` (2) — source-level proof of the zone/
  rule ownership checks
- `TestCommerceOwnershipFixes` (3) — source-level proof of the deposit-
  ownership calls and parent-job verification
- `TestComplianceSelfOnly` (1) — source-level proof of the self-only
  check
- `TestReadPermissionMisuseFixed` (1) — negative control for the fixed
  read-permission-on-write defect
- `TestSetBAdjudication` (3) — full adjudication count, canonical-
  protection count, admin-adjust exclude
- `TestCanonicalClosure` (4) — coverage arithmetic, Set A/B protection
- `TestM01GeoAnd2F35And2F36NonRegression` (4)
- `TestN01FrozenNotRemediated` (2)

**Result: 27/27 passed.**

Every positive assertion has a paired negative control (tenant mismatch
rejected, foreign object non-oracular, missing context rejected, N01
file untouched).
