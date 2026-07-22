# Financial and Credit Safety — Slice 2F-10 (Workstream 13)

## Every path searched
Grepped `customer_router.py` and its 3 connected service files
(`complaint_service.py`, `refund_service.py`, `rework_service.py`) for
credit/deposit/payout/wallet/commission logic.

## Findings
- **The only path with a real internal-credit/security-deposit effect**
  is `customer_respond_to_settlement`'s `accept` branch →
  `_execute_settlement_payout` (canonical `DisputeSettlementService`,
  dual-acceptance gated, unchanged this slice — see
  `settlement-dual-acceptance-boundary.md`).
- **`RefundRequest.requested_amount`** is customer-supplied *input only* —
  it is stored as a request field, never trusted as an approved amount;
  no service method in this router reads it back to authorize a payout.
  Approval/recording of any amount happens exclusively in
  `provider_review_refund` (provider-only, Slice 2F-9-closed) and any
  admin path (out of scope, untouched).
- **No wallet-credit, commission-reversal, or payout code exists anywhere
  in `customer_router`'s reachable service methods** other than the one
  settlement path above.
- **Customer cannot choose a remedy not present in the accepted
  proposal**: `SettlementRespondIn` carries no remedy-type field;
  `proposal.proposal_type` (set at proposal-creation time by whichever
  party proposed it) is never overwritten by the customer's response.

## Requirements verified
- Customer cannot supply a settlement amount trusted by the service — no
  such field exists.
- Customer cannot directly credit their own wallet — no such code path
  exists; the only credit path requires dual acceptance and uses the
  canonical ledger service.
- Customer cannot deduct tenant credit directly — same canonical path,
  same dual-acceptance gate.
- Customer cannot trigger a real-money payout — none exists in this
  codebase's complaint/settlement domain (confirmed by the `refund_service.py`
  module docstring and the absence of any payment-gateway import in
  either connected service file).
- Repeated requests cannot duplicate credit/deposit effects — proven by
  `_check_dual_acceptance`'s status-guard (unchanged, re-verified passing).
