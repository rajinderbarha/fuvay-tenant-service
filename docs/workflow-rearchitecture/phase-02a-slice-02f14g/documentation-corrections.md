# Documentation Corrections to Slice 2F-14F

| File | Original claim | Correction |
|---|---|---|
| `phase-02a-slice-02f14f/tenant-customer-relationship-contract.md` | `ANY_HISTORICAL_SAME_TENANT_RELATIONSHIP` — "every real row is genuine historical evidence of contact" | Superseded — a `Booking` row is NOT reliably genuine evidence: `BookingService.create_booking` lets a `tenant_owner` fabricate one for an arbitrary real customer with zero validation, at a low-trust status (`pending_confirmation`) reachable with a single API call and no customer participation. Fixed this slice: only `CONFIRMED`-or-later Booking statuses now qualify, and generic (non-source-derived) Job rows are excluded entirely. See qualifying-relationship-predicate.md. |
| `phase-02a-slice-02f14f/approval-gate.md` | `CUSTOMER_AUTHORITY_CLOSED` (as part of the overall `SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED` status) | Was accurate given what had been investigated at the time (no relationship-provenance audit had yet been performed). This slice's Workstream 1-2 audit found the low-trust-Booking bootstrap vector, closed the trivially-fixable case (status-gating + legacy-Job exclusion), and disclosed the residual self-confirmation gap as a genuine, out-of-scope architectural issue. Status corrected to `SECURITY_CLOSED_CUSTOMER_AUTHORITY_PROVENANCE_BLOCKED` — see approval-gate.md. |
| `phase-02a-slice-02f14f/manual-customer-authority.md` (2F-14E, carried forward) | "any real platform customer account eligible... when a same-tenant relationship already exists" | The definition of "relationship" itself is corrected this slice — not every historical Booking/Job counts (see qualifying-relationship-predicate.md). |

Preserved, unchanged: the relationship-helper architecture itself, uniform rejection semantics,
disabled/deleted customer rejection, no-partial-persistence proof, route security, source
eligibility and lineage closure, 40/40 field_ops subtotal, 169/210 coverage — none of these were
altered this slice, only the Booking-status and Job-lineage filters inside the existing helper.

No file was deleted. A superseded notice is added to
`phase-02a-slice-02f14f/approval-gate.md` per the established pattern.
