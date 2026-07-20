# Alternate Complaint Route Audit — Workstream 13

## Method
Searched `complaints.admin_router`, `complaints.customer_router`,
rework/warranty/credit-adjacent modules (`customer_credits`,
`platform_commerce`, `finance_hub`), `tenant_engine`, `provider_portal`,
and `execution` routers for equivalent complaint/dispute/rework/
resolution capability.

## Findings

### `complaints.admin_router`
Confirmed: **all** mutations in this file are gated by
`Depends(require_super_admin)` — including SLA/priority mutation,
assignment, provider-response-on-behalf, propose-resolution, reject,
resolve, and close. This is a **stronger**, correctly platform-only
alternate — not a weaker live route. **Disposition: CANONICAL_PLATFORM_ADJUDICATION.**

### `complaints.customer_router`
Uses `get_current_user` only (no permission/role/access-scope guard),
same surface-level pattern as this slice found in `provider_router.py`
**before** this slice's fix. This is the customer's own self-service
router (a different persona, a different module boundary) —
**not audited or modified this slice**, per "do not begin a second
router module." Its own authorization posture (whether
`get_customer_complaint` enforces customer-ownership sufficiently) was
not verified here. **Disposition: REQUIRES_FUTURE_MODULE_SLICE** — logged
as a recommended next module, not begun.

### `customer_credits.DisputeSettlementService`
The canonical, already-audited (FINAL-L5-05J era) credit-ledger service
used by `_execute_settlement_payout`. Re-confirmed as the correct,
canonical owner — not a weaker alternate; this router correctly
delegates to it rather than writing credit balances directly.
**Disposition: CANONICAL_CREDIT_RECOMMENDATION** (the settlement
mechanism is a recommendation-then-dual-acceptance flow, not unilateral
issuance).

### No warranty-claim, rework-creation, or refund-approval alternate found reachable from this router
`create_rework_request_from_complaint`, `approve_rework`/`reject_rework`/
`cancel_rework`, `admin_approve_refund`, `admin_finalize_settlement`,
`admin_start_ai_settlement` all exist in the service layer but are **not
reachable from `provider_router.py`** — confirmed via grep. Their own
router-level guards (if any) were not audited this slice (likely
`admin_router.py`, already confirmed `require_super_admin`-gated above
for the reachable subset).

## Summary table

| Capability | Provider route | Alternate | Canonical owner | Disposition |
|---|---|---|---|---|
| Complaint SLA/priority/assignment/resolve/close | none in provider router | `admin_router` (`require_super_admin`) | `complaints.admin_router` | CANONICAL_PLATFORM_ADJUDICATION (stronger) |
| Customer complaint self-service | none in provider router | `customer_router` (`get_current_user` only) | `complaints.customer_router` | REQUIRES_FUTURE_MODULE_SLICE (not audited, different persona/module) |
| Dual-accepted settlement credit payout | `respond_to_settlement` (this router) | none found | `customer_credits.DisputeSettlementService` | CANONICAL_CREDIT_RECOMMENDATION |
| Rework creation/admin-approval | none in provider router | service-layer methods, router not identified/audited | unresolved (out of scope) | REQUIRES_FUTURE_MODULE_SLICE |
| Refund admin-approval | none in provider router | `admin_approve_refund` (service-layer, router not identified) | unresolved (out of scope) | REQUIRES_FUTURE_MODULE_SLICE |

## Conclusion
No weaker alternate route was found for anything this router itself
mutates. `complaints.customer_router`'s own authorization posture is a
plausible future-slice candidate (it shows the same surface pattern this
slice fixed here), but investigating/fixing it would be starting a
second module — explicitly out of scope, logged instead.
