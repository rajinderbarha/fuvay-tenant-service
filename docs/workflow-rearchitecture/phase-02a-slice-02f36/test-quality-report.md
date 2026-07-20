# Test Quality Report

- Every trusted-tenant helper test (`TestTrustedTenantHelpers`) exercises
  all 4 branches: super_admin exempt, matching tenant allowed, mismatched
  tenant rejected, missing tenant context rejected — not just the happy
  path.
- Appointment ownership tests cover both directions of a potential
  false-negative: same-tenant staff allowed AND foreign-tenant staff
  rejected; customer-owns-own allowed AND customer-touches-other
  rejected; plus the super_admin exemption.
- The bypass-audit test (`TestNoBypassOfClosedRoutes`) required two
  rounds of refinement to eliminate false positives from same-named
  methods on unrelated services (`ServiceCatalogService.create_item` vs
  `InventoryService.create_item`; `CommerceService.create_reservation` vs
  `InventoryService.create_reservation`) — each exclusion is now
  explicitly commented with the reason, not a silent broad exclusion.
- Verifier self-test (`--selftest`) confirms all 23 R01-R23 conditions
  actually fail when forced false — no condition is a silent no-op.
