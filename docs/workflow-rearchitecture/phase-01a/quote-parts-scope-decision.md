# Decision 5 — Quote and Parts Scope

## CORRECTION — Phase 1's finding was wrong; verified via runtime route dump + source read

Phase 1 (and the initial Phase 1A draft) concluded no canonical Parts Request/Approval entity exists. **Live route registration (`scripts/workflow_rearchitecture/list_routes.py`, RUNTIME_VERIFIED) and a source read prove otherwise:**

- `app/engines/execution/models.py:94` — `class PartsRequest(ServiceOSBase)`, table `service_job_parts_requests`, with indexes on `job_id`, `tenant_id`, `status`. Docstring: *"HS8B — real parts request record, replacing the note-only 'needs parts' flag. Technician-created, tenant/business-approved."*
- Fields include: `job_id` (FK to the job), `technician_id`, `part_name`, `quantity`, `estimated_cost`, `reason`, `photo_ids`, `technician_note`, `customer_approval_required`, `business_approval_required`, `status` (default `"requested"`), `approved_by`/`approved_at`, `rejected_by`/`rejected_at`/`rejection_reason`.
- **Live, registered endpoints** (confirmed via runtime route dump against `app.main:app`):
  - `POST /v1/staff/service-jobs/{job_id}/parts-requests` — technician creates a request
  - `GET /v1/staff/service-jobs/{job_id}/parts-requests` — technician lists requests
  - `GET /v1/provider/service-jobs/{job_id}/parts-requests` — tenant/provider lists requests
  - `POST /v1/provider/service-jobs/{job_id}/parts-requests/{parts_request_id}/approve`
  - `POST /v1/provider/service-jobs/{job_id}/parts-requests/{parts_request_id}/reject`
  - `POST /v1/provider/service-jobs/{job_id}/parts-requests/{parts_request_id}/install`
- Backing service methods confirmed in `app/engines/execution/home_service_service.py` (`list_parts_requests`, request-creation logic referencing `PARTS_STATUS_REQUESTED`).

This coexists with, and is separate from, the older `POST /v1/staff/service-jobs/{job_id}/parts-required` flag (which only sets `ServiceJob.status = quote_required`, per Phase 1) and `quote-required` action. The real Parts workflow is a **distinct sub-record of a job**, with its own status machine (`requested → approved/rejected → installed`), not folded into the quote at all.

## Concept separation (revised)

| Concept | Exists today? | Backing model | Notes |
|---|---|---|---|
| Inspection | Yes | `ServiceJob` status `inspection` | technician diagnoses on site |
| Quote | Yes | `quote_checklist` engine (`/customer/quotes`) | customer approves/rejects/revises overall job cost |
| Quote checklist | Yes | `quote_checklist.models` | structured checklist backing a quote |
| Parts Request | **Yes (confirmed, reversing Phase 1)** | `PartsRequest` / `service_job_parts_requests`, linked to `ServiceJob.job_id` | technician creates, tenant/business approves/rejects/installs |
| Parts Approval | **Yes (confirmed)** | Same `PartsRequest.status` machine | `requested → approved/rejected → installed`; supports both `customer_approval_required` and `business_approval_required` flags on the same record |
| Line items | Partial | `quote_checklist` fields | still valid for non-parts additional-work costs |
| Actual parts inventory catalog | Yes, separate | `inventory` engine (`/v1/inventory`) | Confirmed in Phase 1 to have **no FK to job/parts-request** — this remains a true gap: the parts-request `part_name`/`estimated_cost` fields are free text/manual entry, not looked up against the inventory catalog |

## Scope decision (revised)

**What the current canonical workflow supports:** a technician can create a structured, itemized Parts Request against a specific job (part name, quantity, cost estimate, reason, photos), which the tenant/business can approve, reject, or mark installed — a genuine, working, RUNTIME_VERIFIED workflow. Separately, the `customer_approval_required` flag suggests the customer may also need to approve high-value parts requests, though the customer-facing endpoint for this was not found in this pass (UNVERIFIED — recommend a follow-up grep for a customer-facing parts-request approval route before finalizing the Booking Exception workspace's customer-facing parts UI).

**What is genuinely still a gap:** the Parts Request is not linked to any real inventory/stock catalog — `part_name` is free text, not a lookup against the `inventory` engine. A true "parts catalog with stock levels" workflow does not exist. This narrower gap (catalog integration) is what should NOT be fabricated — not the request/approval workflow itself, which is real.

**UI actions now correctly in scope for Phase 2 (reversing the prior exclusion):**
- "Request parts" action on a job (technician), with part name/quantity/cost/reason/photos.
- "Approve/Reject parts request" action (tenant_owner/staff), separate from quote approval.
- "Mark parts installed" action (tenant_owner/staff or technician, TBD by permission check — not traced in this pass).
- Parts request status shown in the Job Detail workspace as its own panel, not merged into the quote panel.

**UI actions still out of scope:**
- Any inventory-stock-check ("is this part in stock") feature — no backend support.
- Any customer-facing parts approval UI, until the `customer_approval_required` flag's actual customer-facing endpoint is confirmed (follow-up item).

## Final technician navigation adjustment (reversing the prior reversal)
The approved navigation spec caps technician nav at 5 items: Today, My Jobs, Inspection and Quote, Work Completion, Profile — with no standalone "Parts" item. Per this corrected decision, Parts Request/Approval is a **real, supported capability** and should be surfaced as a panel/tab within the Job Detail workspace (reached from My Jobs → job detail → "Inspection and Quote" tab group), not as a 6th top-level nav item. This keeps the approved navigation shape intact while correctly exposing the real capability.

## Decision status
**CLOSED — reversed from the incorrect Phase 1/1A-draft finding.** A real Parts Request/Approval entity and full endpoint set exist and are registered at runtime. Phase 2 may build real Parts Request/Approval UI. The only remaining open item is confirming the customer-facing approval path for `customer_approval_required=true` requests (non-blocking follow-up, tracked in `backend-blockers.md`).
