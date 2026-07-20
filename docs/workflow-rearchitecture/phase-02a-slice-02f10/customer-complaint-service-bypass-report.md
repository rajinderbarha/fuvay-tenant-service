# Customer Complaint Service Bypass Report — Slice 2F-10 (Workstream 15)

## Every service method reached by `customer_router`, and every caller
Confirmed via full-repository grep for each method name (excluding test
files) that `customer_router.py` is the **only** production caller of:
`create_complaint`, `list_customer_complaints`, `get_customer_complaint`,
`add_customer_message`, `cancel_customer_complaint`,
`customer_accept_resolution`, `customer_reject_resolution`,
`customer_respond_to_settlement`, `create_refund_request_from_complaint`,
`list_messages` (also called by `provider_router`, with its own
`viewer="provider"` parameter — shared, correctly parameterized, not a
bypass), `list_resolutions`, `list_settlement_proposals`, `get_ai_session`.

## Bypasses found and closed (all 3, detailed in their own documents)
1. `create_complaint` — missing record ownership (see
   `complaint-creation-linkage.md`).
2. `create_refund_request_from_complaint` — missing complaint ownership
   (see `rework-refund-boundary.md`).
3. `_get_resolution` — missing complaint cross-check (see
   `resolution-decision-boundary.md`).

## Ordering defect found and closed
`customer_accept_resolution`/`customer_reject_resolution` — persistence
before transition validation (see `resolution-decision-boundary.md`).

## Confirmed NOT a bypass (shared method, already correctly fixed)
`_get_settlement_proposal`'s `complaint_id` cross-check — Slice 2F-9's
fix already covers both `provider_router` and `customer_router` callers,
since it's the same shared method. Directly re-verified, not assumed.

## No repository-wide complaint-service coverage is claimed
This report covers only the methods directly reachable from
`customer_router`. `complaints.admin_router`'s own service-method callers
were not re-audited (out of scope, unmodified, confirmed
`require_super_admin`-gated).
