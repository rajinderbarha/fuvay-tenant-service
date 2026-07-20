# Customer Complaint Model Lineage — Slice 2F-10

| Model | Table | Customer key | Complaint key | Classification |
|---|---|---|---|---|
| `CustomerComplaint` | `customer_complaints` | `customer_id` | (self, `id`) | CUSTOMER_COMPLAINT_CANONICAL |
| `ComplaintMessage` | `complaint_messages` | `sender_user_id` (when `sender_type=customer`) | `complaint_id` | CUSTOMER_MESSAGE_OR_EVIDENCE (customer/provider shared table, `sender_type` discriminates) |
| `ComplaintMedia` | `complaint_media` | `uploaded_by_user_id` | `complaint_id` | CUSTOMER_MESSAGE_OR_EVIDENCE |
| `ComplaintResolution` | `complaint_resolutions` | n/a (provider-authored; customer only decides) | `complaint_id` | PROVIDER_RESPONSE (creation) / CUSTOMER_RESOLUTION_DECISION (customer's accept/reject mutates `.status`) |
| `SettlementProposal` | `settlement_proposals` | `proposed_by_user_id` (either party) | `complaint_id` | SETTLEMENT_PROPOSAL / DUAL_ACCEPTANCE_SETTLEMENT (status promotion gated by `_check_dual_acceptance`) |
| `ServiceReworkRequest` | (rework_service tables) | via linked complaint | `complaint_id` | REWORK_WORKFLOW — created only as a side effect of `customer_accept_resolution` when `resolution_type == "rework"`; no direct customer rework endpoint exists |
| `RefundRequest` | `refund_requests` | `customer_id` (copied from complaint at creation) | `complaint_id` | REFUND_REQUEST — customer-initiated request only; approval is a separate, provider/admin-only path (`provider_review_refund`, not reachable from customer_router) |
| `AISettlementSession` | (AI settlement table) | via linked complaint | `complaint_id` | AUDIT_OR_HISTORY-adjacent (workflow state, not credit/money) |
| `ComplaintEvent` | `complaint_events` | n/a | `complaint_id` | AUDIT_OR_HISTORY |

## Not present in this router
No `TenantCreditAdjustment`/security-deposit model is directly created by
any `customer_router` mutation — the only path that can affect provider
credit/security-deposit is `_execute_settlement_payout`, reached only via
`customer_respond_to_settlement`'s dual-acceptance branch (canonical
`DisputeSettlementService`, unchanged this slice).

## No legacy/disconnected models found
Every model reached from `customer_router` is the same canonical model
used by `provider_router`/`admin_router` (shared `complaint_service.py`,
`refund_service.py`, `rework_service.py`) — no alternate or legacy
complaint/resolution/settlement implementation exists in this code path.
Confirmed by the single, shared service-layer files already audited in
Slice 2F-9/2F-9A/2F-9B.
