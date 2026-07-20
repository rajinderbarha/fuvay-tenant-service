# Rework and Refund Request Boundary — Slice 2F-10 (Workstream 11)

## Customer capabilities that exist
Only 2 customer-reachable operations touch rework/refund at all:
1. **Rework**: indirectly, only as a side effect of
   `customer_accept_resolution` when the accepted resolution's
   `resolution_type == "rework"` — creates a `ServiceReworkRequest` via
   `ServiceReworkService().create_rework_request_from_complaint`. There is
   **no direct customer route** to request, accept, reject, or confirm
   rework independently of accepting a provider-offered resolution.
2. **Refund**: `request_refund` → `RefundRequestService.create_refund_request_from_complaint`
   — creates a `RefundRequest` in `REFUND_REQUESTED` status only. No
   customer route approves, schedules, or records a refund — those
   remain exclusively `provider_review_refund` (provider_router,
   Slice 2F-9-closed) and any admin-side approval path (not audited this
   slice, out of scope — `complaints.admin_router` untouched).

## Capabilities that do NOT exist for customers (confirmed absent, not assumed)
- Scheduling, starting, or completing provider-side rework — these are
  `ServiceReworkService.schedule_rework`/`mark_rework_in_progress`/
  `mark_rework_completed`, reachable only from `provider_router`
  (tenant-owner-gated, Slice 2F-9-closed).
- Approving a refund — `provider_review_refund`, provider-only.
- Withdrawing a rework or refund request independently (no such route).

## Ownership fix applied this slice
`create_refund_request_from_complaint` previously used a bare
`get_complaint(db, complaint_id)` (fetch-by-id, zero ownership check) —
fixed to require `get_customer_complaint(db, actor_user_id, complaint_id)`
ownership when `actor_type == ACTOR_CUSTOMER`. This is the only
service-layer entry point for customer-initiated refund requests, and the
only caller of this method repository-wide is `customer_router.py`'s
`request_refund` (confirmed via full-repo grep).

## No cash refund mechanism was invented or exists
`RefundRequest` records a request only (`refund_type`, `reason`,
`requested_amount` as customer-supplied *input*, not an approved amount);
no payment-gateway integration or real-money movement occurs anywhere in
this router or its connected service methods — consistent with
`refund_service.py`'s own module docstring, "no real money movement."

## Customer cannot select another tenant's refund request or alter an approved amount
There is no customer route that reads or mutates a `RefundRequest` by ID
at all after creation — the customer only creates the request; every
subsequent state transition (`provider_review_refund`, and any admin
approval) is entirely outside `customer_router`'s reach, so there is no
path for a customer to reference, let alone alter, an approved refund
amount.
