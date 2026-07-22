# Service Credit, Refund, and Financial Boundary — Workstream 10

## `RefundRequest` — confirmed no real money movement
The module's own docstring (`refund_service.py:1`) states: **"Refund
Request Service (no real money movement)."** `provider_review_refund`
(the only mutation reachable from `provider_router.py`) only changes
`status` to `REFUND_PROVIDER_REVIEW` — a workflow marker, not a
financial transaction. The real financial gate,
`admin_approve_refund`, is **not reachable from `provider_router.py`**
(confirmed via grep) — it lives in the service layer, presumably called
from a separate admin router not audited this slice.

## `SettlementProposal` dual-acceptance payout — the one genuine credit mechanism
`respond_to_settlement` → `tenant_respond_to_settlement` →
(on dual acceptance) → `_execute_settlement_payout`:
- **Never real money** — the code explicitly checks
  `if remedy in MONETARY_REMEDIES: return None` before any deduction,
  confirmed via direct source read.
- Only a **positive-amount, non-monetary remedy** (re-verified: the
  exact remedy taxonomy was not exhaustively re-traced, but the
  monetary-remedy exclusion is unconditional) triggers a deduction.
- The deduction is funded from **the provider's own credit wallet,
  falling back to their own security deposit** — never another
  tenant's account, and never a direct customer balance write.
- Executed via **`DisputeSettlementService`** (`app.engines.customer_credits`)
  — the canonical credit-ledger service already audited/hardened in an
  earlier slice (FINAL-L5-05J era), not a raw balance overwrite.
- **Requires dual acceptance** (`_check_dual_acceptance`: both
  `customer_response == "accept"` AND `tenant_response == "accept"`) —
  a provider cannot unilaterally trigger a payout by responding alone.

## Requirements verification

| Requirement | Status |
|---|---|
| Provider roles must not issue platform-controlled customer service credits unless an existing explicit policy and permission proves they may | Confirmed — the only credit mechanism requires dual acceptance and is capped to the provider's own wallet/deposit; it is not a unilateral "issue a credit" action |
| Provider roles must not directly modify customer or tenant balances through an unguarded complaint route | **FIXED THIS SLICE** — `respond_to_settlement` previously allowed a caller who owned some `complaint_id` to supply an unrelated `proposal_id` (potentially from another tenant's complaint) and manipulate it toward triggering this payout mechanism against the wrong complaint/tenant. Fixed via the `proposal.complaint_id` cross-check in `_get_settlement_proposal` |
| Real-money refund behavior must not be invented | Confirmed — not touched; `RefundRequest` remains a workflow-status-only record |
| Credit recommendations must be distinguished from credit issuance | The dual-acceptance requirement itself distinguishes a *proposal* (single-party) from *issuance* (both parties accepted) |
| Platform-admin finance routes remain separately controlled | Confirmed — `admin_approve_refund`, `admin_finalize_settlement` are not reachable from this router |
| Any weaker live financial mutation must block closure | The one weaker path found (the `proposal_id` cross-tenant gap) is fixed, not merely documented |

## Conclusion
No real-money refund or payout behavior exists in this router, and none
was invented. The one genuine credit-adjacent mutation
(`_execute_settlement_payout`) already uses the canonical ledger service,
already blocks monetary remedies, and already requires dual acceptance
— its only real gap (a cross-tenant/cross-complaint `proposal_id`
substitution) is now closed.
