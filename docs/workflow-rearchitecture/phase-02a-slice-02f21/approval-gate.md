# Slice 2F-21 Approval Gate

## Final status

**NEXT_MODULE_SELECTED_COVERAGE_UNCHANGED**

This is a discovery/verification/selection slice. `SECURITY_CLOSED` is
not claimed and is not applicable — no authorization module was
implemented, per this slice's own explicit instruction.

## Coverage
**206 protected of 226** tenant/provider mutations — UNCHANGED.
**20 unprotected across 9 modules.**

Reconciliation arithmetic (row-level evidence only, per
`canonical-coverage-reconciliation.md`):
- Numerator: 206 + 0 newly-discovered-protected − 0 incorrectly-counted = **206**
- Denominator: 226 + 0 missing − 0 false-positive − 0 non-tenant − 0 duplicate − 0 deprecated = **226**

All 20 remaining rows classified `GENUINE_UNPROTECTED_TENANT_MUTATION`;
zero reclassified. Zero row-level evidence justified any correction.

## Selected next module (Slice 2F-22)
`app.engines.package_commerce.tenant_router` — **1 mutation route**:
`POST /v1/tenant/packages/{package_id}/purchase` (`tenant_purchase_package`).

Selected on evidence re-derived from current source, not carried over
from the prior queue ranking. Beyond confirming the prior
`PERMISSION_ONLY_NOT_SCOPE_AWARE` gap, this slice surfaced a previously
undocumented `CLIENT_AMOUNT_TRUSTED`-class gap on the handler's
`mark_paid` field, raising the route's severity to HIGH. Requires no new
role or permission (`require_tenant_owner_mutation` is a direct drop-in),
no migration, no pipeline merge, and has no blocking product decision.

## Findings requiring attention (NOT clean)

This slice did **not** produce a clean regression result, and does not
claim one.

**A real regression caused by Slice 2F-20 was found and fixed.**
`test_phase2f19_remaining_queue_reconciliation.py`'s baseline assertion
still read `protected == 200` after 2F-20 advanced the numerator to 206 —
2F-20 updated two of three recount assertions and missed the third. It
had been failing since 2F-20 merged. Fixed this slice (recount tests are
explicitly permitted); the full recount set now passes 105/105.

**Slice 2F-20's regression report was materially wrong and has been
retracted in place.** Its "45 failed / 11010 passed / zero regressions"
conclusion is unsupported; the true deterministic figure is 87 failed /
11057 passed / 111 errors / 14 skipped (86 failed post-fix). Its
verification method — grepping failure output for module keywords — was
incapable of detecting the regression it missed. Prior slices using the
same method should be treated as UNVERIFIED on this point. See
`documentation-corrections.md` and `regression-report.md`.

**Two stale Slice-2D-era canary tests remain failing and were NOT
fixed** (`test_phase2d_tenant_access_model.py`). They assert about
application structure that approved later slices legitimately changed;
resolving them requires revisiting `tenant-readonly-decision.md`'s
conclusion, which is a product decision, not a mechanical recount, and
2F-21 is prohibited from changing application authorization behavior.
Recorded in `known-limitations.md` and `product-decisions-required.md`.

## Attributable to Slice 2F-21 itself: zero failures
No file under `app/` was modified. One new test file added (28 tests, all
passing). One stale recount assertion corrected.

## Preserved (re-confirmed)
- `field_ops.router` 28/28; `field_ops.staff_router` 6/6.
- Booking authorization/provenance closure intact.
- Quote-checklist and invoice-lineage closures intact.
- Platform-notifications/chat-media closure (2F-18…2F-18E) intact.
- Compliance provider security closure (2F-20) intact — confirmed by
  route-level proof, not by assumption
  (`compliance-indirect-change-audit.md`: 2F-20 touched only files under
  `app/engines/compliance/`; none of the 20 remaining routes' modules
  import anything under that path, so zero indirect protection was
  credited).
- Compliance export workflow NOT reopened, per scope prohibition — its
  `DOMAIN_INTEGRITY_BLOCKED` status stands untouched.
- `PartsRequest` ServiceJob-only; `Booking`/`ServiceBooking` and
  `field_ops.Job`/`ServiceJob` separate.
- Canonical roles only; no alias, role, or permission added.
- `readonly@demo-ac-services.local` untouched.
- Migration 144 unapplied; no migration added or applied.

## Scope discipline confirmed
No application authorization code changed. No route dependency added. No
service authorization changed. No migration, no pipeline merge. No
frontend/mobile or visual work. No `My Work`/Next-Action work. No
Booking Exception Resolution. The selected module was NOT implemented —
only selected, scoped, and planned.

## Stop condition
This response stops at the Slice 2F-21 approval gate. Implementation of
`app.engines.package_commerce.tenant_router` has not begun and is
deferred to Slice 2F-22, per the plan in `selected-next-module.md`,
`selected-next-module-security-plan.csv`, and
`selected-next-module-boundaries.md`.

## Forward annotation (added by Slice 2F-22)
Slice 2F-22 implemented the module selected here
(`app.engines.package_commerce.tenant_router`, its sole mutation
`POST /v1/tenant/packages/{package_id}/purchase`). The selection was
CONFIRMED CORRECT and the route is now protected: coverage advanced
**206/226 -> 207/226**, leaving 19 unprotected across 8 modules.

Two corrections to this slice's findings, both recorded in
`../phase-02a-slice-02f22/documentation-corrections.md`:

1. **Gap terminology.** 2F-21 labelled the `mark_paid` defect
   `CLIENT_AMOUNT_TRUSTED`. That is wrong -- no monetary amount was ever
   accepted from the client (price, credits, deposit, quota and validity were
   already server-derived from the `ServicePackage` record). The correct
   label is `CLIENT_SETTLEMENT_ATTESTATION_TRUSTED`: the tenant could assert
   *that* payment occurred, never *how much*.
2. **Related-read count.** 2F-21 listed 4 related reads; the router declares
   8. The four omitted are the financially sensitive ones (credit wallet,
   credit ledger, commissions, storage quota). All 8 were audited and found
   correctly tenant-scoped. The omission did not affect the selection.

2F-21 also **understated** the defect's severity, which 2F-22 traced:
`activate_tenant_package_assignment` orders activation candidates by
`paid_at DESC NULLS LAST`, so a self-attested "paid" row was actively
PREFERRED for activation -- and activation is what grants wallet credits,
storage quota and commission rate.

This slice's own regression-methodology correction was applied in full:
2F-22 proved regression safety by exact failing-node-ID comparison (zero
newly failing, one resolved), not by keyword-grepping failure output. The two
stale Slice-2D canaries were left untouched, as this slice required.

Final status for 2F-22:
`SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED`.
See `../phase-02a-slice-02f22/approval-gate.md`.
