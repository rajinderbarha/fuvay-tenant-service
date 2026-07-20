# Approval Gate — Slice 2F-6A

## Status
**SECURITY_AND_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**

All 4 mutation routes on `invoice_payment.provider_router` now enforce
correct persona/access-scope authorization (re-verified, unchanged
security posture from Slice 2F-6, plus the technician-narrowing
correction). Both conclusively-provable financial-integrity defects
identified in this slice's mission — `record_onsite_payment`'s missing
amount/state validation, and `add_item`'s missing quantity/price
validation — are fixed. Duplicate final actions (repeat issue, repeat
payment, duplicate invoice-per-job) are all rejected. Cross-tenant
targeting is directly proven rejected on all 4 routes via
dependency-level tests with real mismatched tenant IDs, producing no
mutation. No confirmed integrity defect remains open.

This is "product policy blocked" rather than fully closed because three
questions remain deliberately unresolved, none of which block security
or financial-integrity closure: (1) whether staff/technician should ever
get `FIELD_OPS_INVOICE_GEN`, (2) whether technician should ever be
widened into the 3 staff-gated capabilities if a mobile client is later
built, (3) a cosmetic frontend button-visibility gap (backend
authoritative, no security impact).

## Quality gates (27) — summary
All satisfied. Full itemized evidence is distributed across the other 14
files in this directory (policy matrix, technician decision, state
machine, payment/item integrity, duplicate/concurrency review,
cross-tenant test matrix, frontend exposure, direct test CSV, product
decisions, test report, known limitations, deferred items).

## Distinguishing the three closure dimensions
- **AUTHORIZATION_CLOSED**: yes — every mutation has correct persona/
  access-scope enforcement, wrong roles and read-only scope are denied,
  cross-tenant access is denied (re-verified, technician narrowed).
- **FINANCIAL_INTEGRITY_CLOSED**: yes — invalid payment amounts
  (negative/zero/overpayment) rejected, invalid invoice-item values
  (negative quantity/price) rejected, state transitions enforced,
  duplicate final actions prevented, denied requests produce no
  mutation, no confirmed integrity defect remains open.
- **PRODUCT_POLICY_CLOSED**: blocked — technician/staff capability
  extent and `FIELD_OPS_INVOICE_GEN` ownership remain open questions;
  frontend exposure does not yet fully match the final backend policy
  (cosmetic gap, documented).

## Stop condition honored
Per instruction, this slice stops here. No second new module was begun.
No previously-closed module was modified beyond `invoice_payment.provider_router`
itself. No permission was granted (`FIELD_OPS_INVOICE_GEN` was not
extended to any new role). No payment-gateway behavior was introduced.
`readonly@demo-ac-services.local` was not touched. Migration 144 was not
applied.
