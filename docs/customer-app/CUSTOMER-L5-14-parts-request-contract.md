# CUSTOMER-L5-14 — Parts Request Contract (execution engine, NOT used by this client)

This doc exists to record, precisely, why the spec's literal "parts
approval" model was investigated and rejected as this sprint's real
backend target — see baseline-verification.md's Central Finding.

## Model: `PartsRequest` (`app/engines/execution/models.py` lines 94–144)

Table `service_job_parts_requests`. Fields: `job_id`, `tenant_id`,
`technician_id`, `part_name`, `quantity`, `estimated_cost`, `reason`,
`photo_ids` (bare JSONB array, no FK), `technician_note`,
`customer_approval_required` (bool, default false),
`business_approval_required` (bool, default true, always set true by
`create_parts_request` regardless of input), `status`, `approved_by`/
`approved_at`, `rejected_by`/`rejected_at`/`rejection_reason`,
`request_id`.

## Real endpoints (`execution/home_service_router.py`)

- Staff: `POST /v1/staff/service-jobs/{job_id}/parts-requests` (create),
  `GET /v1/staff/service-jobs/{job_id}/parts-requests` (list).
- Provider/business: `GET /v1/provider/service-jobs/{job_id}/parts-requests`
  (list), `POST .../{parts_request_id}/approve`, `POST
  .../{parts_request_id}/reject`, `POST .../{parts_request_id}/install`.
- Customer: **none.** `customer_router` in the same file only exposes
  `GET /{job_id}/tracking` (CUSTOMER-L5-13) — it never touches
  `PartsRequest`.

## Why this cannot be the sprint's real feature

`approve_parts_request` (business/provider action) can move a request to
`PARTS_STATUS_CUSTOMER_APPROVAL_PENDING` when
`customer_approval_required=true`, but no service method anywhere sets
`PARTS_STATUS_CUSTOMER_APPROVED` or `PARTS_STATUS_CUSTOMER_REJECTED` —
grepped across the entire `app/engines` tree, both constants are only
ever referenced inside `install_parts_request`'s status-membership
checks, never assigned. A part routed for customer decision is
permanently stuck, and `complete_job`'s own resolution gate
(`ERR_UNRESOLVED_PARTS_REQUESTS`) only checks for the earlier
`PARTS_STATUS_REQUESTED` status — it doesn't even notice the stuck
`customer_approval_pending` record. There is no reachable customer action
to build a screen against.

## What this client does instead

Nothing — this model is not wired into any screen this sprint. If a
future sprint adds the missing customer endpoints
(`GET/POST /v1/customer/service-jobs/{jobId}/parts-requests/...`), a
client feature could be built the same way `quote-decision` was built
this sprint. Until then, this remains a documented, disclosed backend gap
— see `known-gaps.md`.
