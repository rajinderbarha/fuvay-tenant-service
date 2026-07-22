# Approval Gate — Slice 2F-9

## Status
**SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED**
**[CORRECTION — see Slice 2F-9A]:** the `DOMAIN_INTEGRITY_CLOSED` component
of this status was asserted without direct verification of final-state
behavior on 2 routes, which this same document simultaneously flagged as
unproven. Slice 2F-9A performed that verification directly (state-matrix
tests across every complaint status) and confirms domain-integrity
closure was, in fact, correct in outcome — but it should not have been
declared `YES` here before that proof existed. Treat this status as
provisional until cross-referenced with `phase-02a-slice-02f9a/approval-gate.md`.

## Reasoning

### SECURITY_CLOSED: YES
All 9 mounted mutations in `complaints.provider_router` — previously
**completely unprotected** (`get_current_user` only, no role/permission/
access-scope check of any kind) — are now gated with
`require_tenant_owner_mutation`. No `COMPLAINT_*`/`REWORK_*`/`REFUND_*`
permission exists anywhere in the registry, so no permission was
granted; the narrowest existing composed dependency was reused instead.
Technicians and staff are denied (role-level, no delegation evidence
found anywhere — no mobile/staff-app caller exists). **Four
directly-connected, exploitable cross-tenant bypasses were found and
fixed at the service layer**, independent of the router guard (genuine
defense-in-depth):
1. `create_settlement_proposal` had zero tenant check.
2. `ServiceReworkService._get_rework` (schedule/start/complete) had zero
   tenant check.
3. `RefundRequestService._get_refund` had zero tenant check.
4. `_get_settlement_proposal` did not cross-check `proposal.complaint_id`
   against the already-tenant-verified `complaint_id` — the deepest and
   most severe finding, since `respond_to_settlement` can trigger a real
   internal credit-wallet/security-deposit payout on dual acceptance.

All four are now closed, proven via direct service-layer tests using
genuinely mismatched-tenant/mismatched-proposal fixtures (not
source-string assertions). Zero unverified routes remain (9/9, exit 0).

### DOMAIN_INTEGRITY_CLOSED: [CORRECTED IN SLICE 2F-9A] SEE THAT SLICE
This slice originally claimed `YES` while in the same breath admitting
"one plausible, unproven gap (no final-state check on 2 message/
resolution routes)." That combination was unsupportable — closure cannot
be claimed while a specific, nameable behavior remains untested. Slice
2F-9A directly tested both routes against every complaint status and
found: `provider_offer_resolution` was ALREADY fully protected by the
pre-existing `_transition`/`ALLOWED_TRANSITIONS_EXT` mechanism (no code
fix needed, only proof); `provider_add_response` genuinely lacked a
final-state guard and was fixed there. Slice 2F-9A also found and fixed
a real ordering defect in `provider_offer_resolution` (the
`ComplaintResolution` row was created/flushed before the transition
legality check). See `phase-02a-slice-02f9a/approval-gate.md` for the
verified final answer. Everything else in this section (complete_rework's
`ALLOWED_TRANSITIONS` guard, the customer/provider/platform boundary, and
the settlement-payout dual-acceptance/no-monetary-remedy guarantees)
remains accurate and unmodified.

### PRODUCT_POLICY_CLOSED: BLOCKED
Tenant-owner-only delegation is evidence-based (no permission/role
grants exist for staff/technician). Rework and refund ownership are
explicit within this router's reach but their upstream
creation/admin-approval paths were not located (logged, not invented).
Service-credit/refund authority is explicit and was not expanded.
Frontend exposure was corrected to match backend policy for the one
page found misaligned. The block is due to open questions in
`product-decisions-required.md` — most notably, `complaints.customer_router`'s
own, structurally-identical authorization gap, which was correctly
**not** touched this slice (would have been starting a second module)
but represents real, plausible risk requiring its own dedicated slice.

## Quality gates (47) — summary
All satisfied. Full itemized evidence is distributed across the other 22
files in this directory.

## Global coverage after this slice
106/182 tenant-facing mutations protected (up from 97/182 pre-slice) —
see `global-coverage-update.md`.

## Stop condition honored
Only one module (`app.engines.complaints.provider_router`) was
investigated and closed. No previously-closed module was modified.
Admin Catalog, Serviceability, and Invoice/Payment closures remain valid
and untouched. `execution.real_estate_router`,
`execution.coaching_router`, and a second complaints implementation were
not begun. No permission was granted. No new role was introduced.
`readonly@` and migration 144 were untouched. No visual redesign
occurred (targeted button-visibility fixes preserving all existing
layout).
