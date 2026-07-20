# Test Quality Report

- Every trusted-tenant helper test (`TestTrustedTenantHelpers`) exercises
  all 4 branches: super_admin exempt, matching tenant allowed, mismatched
  tenant rejected, missing tenant context rejected — for all 3 services
  that gained the helper this slice.
- `TestPricingZoneRuleOwnership` and `TestCommerceOwnershipFixes` assert
  against actual source code (`inspect.getsource`), not just behavioral
  mocks, to prove the specific ownership-check lines exist in the running
  code, not merely documented as intended.
- `TestReadPermissionMisuseFixed` is a dedicated negative-control test
  proving the read-permission-for-write defect on `recalculate_badges`
  was actually fixed, not just documented.
- `TestN01FrozenNotRemediated` is an unusual but deliberate test: it
  proves the ABSENCE of a change (no 2F-37 marker in N01 media files),
  serving as a regression guard against a future accidental scope
  violation of the frozen contract.
- Verifier self-test (`--selftest`) confirms all 21 R01-R21 conditions
  actually fail when forced false — no condition is a silent no-op.
