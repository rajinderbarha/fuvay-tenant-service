# HS8B — Parts Request Approval Report

## Result: real workflow implemented and live-verified

New table `service_job_parts_requests` (migration 128) + `PartsRequest`
model with the ticket's exact field set (part_name, quantity,
estimated_cost, reason, photo_ids, technician_note,
customer_approval_required, business_approval_required, status,
approved_by/at, rejected_by/at, rejection_reason, request_id).

Statuses implemented: `requested`, `business_approved`,
`business_rejected`, `customer_approval_pending`, `customer_approved`
(reachable via the `customer_approval_required` flag, not yet exercised
by any real customer-facing flow — see Remaining Blockers),
`customer_rejected` (same caveat), `installed`, `cancelled` (status enum
value exists; no cancel endpoint wired yet).

## Endpoints (real, live-verified)
- `POST /v1/staff/service-jobs/{job_id}/parts-requests` — technician creates.
- `GET /v1/staff/service-jobs/{job_id}/parts-requests` — technician lists.
- `GET /v1/provider/service-jobs/{job_id}/parts-requests` — tenant lists.
- `POST /v1/provider/service-jobs/{job_id}/parts-requests/{id}/approve` — tenant approves.
- `POST /v1/provider/service-jobs/{job_id}/parts-requests/{id}/reject` — tenant rejects.
- `POST /v1/provider/service-jobs/{job_id}/parts-requests/{id}/install` — mark installed.

## Live-verified scenarios (real job, real DB)
1. Create with valid data → `201`-equivalent `200`, `status: requested`.
2. Create with empty `part_name` → `422 PART_NAME_REQUIRED`.
3. Approve as tenant (`provider@serviceos.in`) → `status: business_approved`.
4. Install approved request → `status: installed`.
5. Create a second request, reject it (`reason: "Not needed for this repair"`) → `status: business_rejected`.
6. Try to install the rejected request → `422 PARTS_REQUEST_REJECTED_CANNOT_INSTALL`.

## What's real vs. documented as future scope
- **Business approval: fully real and live-verified.**
- **Customer approval: schema exists (`customer_approval_required` flag,
  `customer_approval_pending`/`customer_approved`/`customer_rejected`
  statuses) but no customer-facing endpoint or UI calls it.** Per the
  ticket's own instruction ("If customer approval is not supported yet,
  keep business approval only and document customer approval as future
  scope"), this is documented, not claimed as working.
- "Request More Info" (tenant action) and "Cancel own pending request"
  (technician action) from the ticket's action lists were not
  implemented — only Approve/Reject and Create/List.

## Verdict
Parts request workflow: **real, implemented, and live-verified** for the
core create → approve/reject → install cycle. Not
`NOT_READY_HS8_PARTS_REQUEST_FAILED`.
