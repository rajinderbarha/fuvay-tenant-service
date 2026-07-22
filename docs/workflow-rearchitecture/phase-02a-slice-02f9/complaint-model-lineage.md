# Complaint Model and Record Lineage — Workstream 2

| Model | Table | Tenant key | Customer key | Job/booking key | Parent | Classification |
|---|---|---|---|---|---|---|
| `CustomerComplaint` | `customer_complaints` | `tenant_id` | `customer_id` | `booking_id`/`job_id` | none (root) | **CUSTOMER_COMPLAINT_CANONICAL** |
| `ComplaintMessage` | `complaint_messages` | `tenant_id` (denormalized) | via parent complaint | via parent | `complaint_id` | **MESSAGE_OR_EVIDENCE** — has a `visibility` enum (`public_to_case`/`customer_only`/`provider_only`), but the provider-response endpoint hardcodes `public_to_case` regardless of client input (see `note-evidence-privacy.md`) |
| `ComplaintMedia` | `complaint_media` | via parent | via parent | via parent | `complaint_id` | **MESSAGE_OR_EVIDENCE** — same `visibility` enum, not independently traced for write endpoints in this router (no media-upload route exists in `provider_router.py`) |
| `ComplaintEvent` | `complaint_events` | `tenant_id` | n/a | n/a | `complaint_id` | **AUDIT_OR_HISTORY** — append-only event log |
| `ComplaintResolution` | `complaint_resolutions` | `tenant_id` | n/a | n/a | `complaint_id` | **PROVIDER_COMPLAINT_RESPONSE** — a provider-proposed resolution, `status` defaults to `"proposed"` |
| `ServiceReworkRequest` | `service_rework_requests` | `tenant_id` | `customer_id` | `job_id`/`original_job_id` | `complaint_id` | **REWORK_WORKFLOW** |
| `RefundRequest` | `refund_requests` | `tenant_id` | `customer_id` | `booking_id`/`job_id`/`invoice_id` | `complaint_id` | **REWORK_WORKFLOW**-adjacent (module docstring: `"no real money movement"` — see `service-credit-refund-boundary.md`) |
| `SettlementProposal` | `settlement_proposals` | `tenant_id` | n/a directly (via complaint) | n/a | `complaint_id` | **PLATFORM_COMPLAINT_ADJUDICATION**-adjacent — `proposed_by` distinguishes customer/provider/AI origin; dual-acceptance can trigger a real credit-wallet/security-deposit payout (`_execute_settlement_payout`) — genuinely money/credit-moving, not just workflow state |
| `AISettlementSession` | `ai_settlement_sessions` | via parent | n/a | n/a | `complaint_id` | **PLATFORM_COMPLAINT_ADJUDICATION**-adjacent — AI-mediated Q&A leading to a settlement proposal |
| `ComplaintPolicy` | `complaint_policies` | not independently traced this slice | — | — | — | not reached by any route in `provider_router.py`; not classified further, out of this router's boundary |

## Notes
- No separate `CustomerServiceCredit`/`TenantCreditAdjustment`/`WarrantyClaim`
  model was found anywhere in `app.engines.complaints` — the only credit/
  financial mechanism reachable from this router is the settlement
  proposal's dual-acceptance payout (`_execute_settlement_payout`,
  funded from "the provider's credit wallet and then their security
  deposit," per the code's own comment — **never real money**).
- No models were merged. `ServiceReworkRequest`, `RefundRequest`, and
  `SettlementProposal` remain distinct, separately-keyed record types.
