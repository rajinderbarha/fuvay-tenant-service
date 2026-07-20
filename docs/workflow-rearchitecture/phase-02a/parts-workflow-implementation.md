# Parts Request/Approval Workflow Implementation

## Pre-implementation verification (per Workstream 10's explicit checklist)

All items below were verified against the running codebase before any frontend work began:

| Item | Verified how | Result |
|---|---|---|
| Runtime route registration | `scripts/workflow_rearchitecture/list_routes.py` (Phase 1A) + direct source read this phase | `POST/GET /v1/staff/service-jobs/{id}/parts-requests`, `GET/POST /v1/provider/service-jobs/{id}/parts-requests(/{id}/approve\|reject\|install)` all registered and live |
| ServiceJob foreign-key behavior | `app/engines/execution/models.py:94` (`PartsRequest.job_id`) | `PartsRequest` links to `ServiceJob` via `job_id`, `tenant_id`, `technician_id` — no link to Booking or field_ops Job exists |
| Technician creation permissions | `app/engines/execution/home_service_router.py` staff_router | Gated by `get_current_user` + staff-id resolution (same pattern as job status-transition endpoints) |
| Provider/admin approval permissions | `home_service_router.py` provider_router | Gated by `get_current_user`; tenant-scoped via `tenant_id` on every query |
| Reject behavior | `home_service_service.py::reject_parts_request` | Sets `status` to `business_rejected`/`customer_rejected`, records `rejected_by`/`rejected_at`/`rejection_reason` |
| Install behavior | `home_service_service.py::install_parts_request` | Only callable when `status` is `business_approved`/`customer_approved`; sets `PARTS_STATUS_INSTALLED` |
| Status transitions | `app/engines/execution/constants.py` | `requested → business_approved/customer_approval_pending → customer_approved → installed`, or `→ business_rejected/customer_rejected` |
| Quote linkage | Source read | None — `PartsRequest` is a sibling record to `quote_checklist`, not nested inside a quote. Confirmed no FK between the two. |
| Notification behavior | Not traced this phase | UNVERIFIED — no notification call was found wired to parts-request state changes in the reviewed code path; not fabricated in the UI (no "notification sent" copy was added) |
| Audit behavior | Not traced this phase | UNVERIFIED — no dedicated audit-log write was found for parts-request actions; not claimed in the UI |
| Existing tests | `tests/test_sprint21_execution.py` | No parts-request-specific tests existed before this phase; this phase's `tests/test_phase2a_my_work.py` covers My Work's *derivation* of parts-request items, not the parts-request service methods themselves (see `known-limitations.md`) |

## What was implemented

### Technician side (`frontend/tenant-portal/app/staff/jobs/[job_id]/page.tsx`)
- New "Parts Requests" panel with:
  - A create form (part name, quantity, estimated cost, reason) calling the pre-existing `homeServiceStaffJobsApi.createPartsRequest` client method (which existed in `lib/api.ts` but was never called from any UI before this phase).
  - A list of existing requests for the job, calling the pre-existing `homeServiceStaffJobsApi.listPartsRequests` method, with status badges (`requested`, `business_approved`, `installed`, etc. — real backend status strings, human-readable via `.replace(/_/g, " ")`, not relabeled or reinterpreted).

### Provider/tenant side (`frontend/tenant-portal/app/(tenant)/service-jobs/[id]/execution/page.tsx`)
- This page already had a working Parts Requests panel with Approve/Reject buttons (built in an earlier phase, HS8B). This phase added the missing **Mark Installed** button for requests in `business_approved`/`customer_approved` status, wiring the pre-existing `homeServiceExecutionApi.installParts` client method that had no caller anywhere in the codebase before this change.

## Restrictions honored

- **"Parts Request"/"Parts Approval" used only for real `PartsRequest` records** — no quote line item, additional-work note, or inspection finding is labeled as a parts request anywhere in the new UI.
- **No Parts UI for Booking or field_ops Job** — both touched pages (`/staff/jobs/[job_id]` and `/service-jobs/[id]/execution`) exclusively operate on `ServiceJob` records (confirmed by their existing API calls, `homeServiceStaffJobsApi`/`homeServiceExecutionApi`, both scoped to `/v1/staff/service-jobs` and `/v1/provider/service-jobs`). Neither page ever renders a Booking or field_ops Job record, so no conditional gating logic was needed to prevent Parts UI from appearing on an incompatible record — the pages are already single-purpose.
- **No cross-pipeline adapters created.**
- **No inventory integration fabricated** — the create form is a plain text/number entry (part name, quantity, cost), matching the real backend model's free-text `part_name` field; no stock lookup, no inventory-engine call was added.
- **Distinct concepts kept distinct in the UI:** the job detail page's existing Quote/Completion actions (`quote_required`, `complete`) remain entirely separate UI elements from the new Parts Request panel — no visual or functional merging occurred.

## Tests
- `tests/test_phase2a_my_work.py` — 8 of its 13 tests cover parts-request status derivation logic (as consumed by My Work), including the deliberate absence of a fabricated technician-facing install action.
- **Not added this phase:** direct unit tests for `create_parts_request`/`approve_parts_request`/`reject_parts_request`/`install_parts_request` service methods themselves (these predate this phase and were out of its scope; see `known-limitations.md`) or Playwright/frontend component tests for the new form (no frontend test runner was exercised this phase — see `regression-test-report.md`).
