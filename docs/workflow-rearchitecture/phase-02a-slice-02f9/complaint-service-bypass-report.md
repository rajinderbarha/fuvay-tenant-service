# Complaint Service Bypass Report — Workstream 14

## Methods audited
`provider_add_response`, `provider_offer_resolution`,
`create_settlement_proposal`, `tenant_respond_to_settlement`,
`schedule_rework`, `mark_rework_in_progress`, `mark_rework_completed`,
`provider_review_refund`, `AISettlementService.submit_answers`.

## Callers
Each method has exactly one caller: the corresponding endpoint in
`complaints/provider_router.py`. Confirmed via targeted grep — no other
router or worker calls these specific methods.

## Tenant ID source verification and fixes applied
Three methods had **zero tenant ownership check** before this slice —
directly-connected, exploitable cross-tenant bypasses, now fixed:

1. **`create_settlement_proposal`** — used `_get_complaint` (no tenant
   check) instead of `provider_get_complaint`. Fixed: now uses
   `provider_get_complaint` when a `tenant_id` is supplied.
2. **`ServiceReworkService._get_rework`** (used by `schedule_rework`,
   `mark_rework_in_progress`, `mark_rework_completed`) — loaded by
   `rework_id` alone. Fixed: accepts an optional `tenant_id`, rejects a
   mismatch with the same not-found error a missing row would produce.
3. **`RefundRequestService._get_refund`** (used by
   `provider_review_refund`) — same gap, same fix pattern.

A **fourth**, deeper bypass was found and fixed in
`tenant_respond_to_settlement`/`customer_respond_to_settlement`:
`_get_settlement_proposal` loaded by `proposal_id` alone, without
verifying `proposal.complaint_id == complaint_id` — meaning even a
caller who had already proven ownership of `complaint_id` could supply
an unrelated (or foreign-tenant) `proposal_id` and manipulate it,
potentially reaching the real credit-wallet/security-deposit payout
mechanism (`_execute_settlement_payout`) against the wrong
complaint/tenant/customer. Fixed via a `complaint_id` parameter on
`_get_settlement_proposal`.

## Ownership verification (already correct, unmodified)
`provider_get_complaint` (used by `respond_to_complaint`,
`offer_resolution`, `submit_ai_answers`, and now `create_settlement_proposal`/
`respond_to_settlement`) correctly compares `complaint.tenant_id` against
the caller's tenant — pre-existing, re-verified, unmodified.

## Transaction boundaries
Each mutation commits within its own request; no cross-request spanning.
No row/advisory lock exists anywhere in this module (same platform-wide,
pre-existing pattern documented in prior slices) — not redesigned here.

## Audit behavior
`_log_event` (writing `ComplaintEvent` rows) is called by most mutation
paths (`provider_add_response` does **not** log an event — confirmed via
source read — while `offer_resolution`, rework, and refund paths do).
This asymmetry is logged as a known limitation, not fixed (a design
choice, not a mechanical gap).

## Service-layer defense-in-depth
Now genuinely present for all 9 routes: `provider_get_complaint`'s
tenant check (pre-existing) plus the 4 newly-added tenant/complaint
cross-checks in `_get_rework`, `_get_refund`, `create_settlement_proposal`,
and `_get_settlement_proposal` — independent of the router-level
`require_tenant_owner_mutation` guard.

## Conclusion
4 directly-connected bypasses found and fixed (3 tenant-ownership gaps +
1 deeper complaint/proposal cross-reference gap). No other bypass found.
One audit-coverage gap (`provider_add_response` doesn't log an event)
documented, not fixed.
