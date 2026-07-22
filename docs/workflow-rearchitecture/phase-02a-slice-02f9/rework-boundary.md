# Rework Boundary — Workstream 9

## What rework is
A **separate record** (`ServiceReworkRequest`, `service_rework_requests`
table) linked to a `CustomerComplaint` via `complaint_id`, and to the
original `ServiceJob` via `original_job_id`/`job_id`. It is **not** a
complaint status alone, **not** a new `ServiceJob`, and **not** a
quote/checklist workflow.

## Creation
`create_rework_request_from_complaint` is the creation method — **not
reachable from `provider_router.py`** (confirmed via grep: this method
name does not appear anywhere in `provider_router.py`). This means the
provider-facing router this slice audits can only **schedule, start, and
complete** an already-existing rework request — it cannot fabricate one
from scratch. Creation must happen through a different, unaudited path
(likely the customer-facing or admin router, not investigated this
slice — out of scope).

## Approval
`approve_rework`/`reject_rework` (admin-only methods) are **not
reachable from `provider_router.py`** either — confirmed via grep. A
provider cannot approve their own rework request through this router.

## Traced lifecycle (within this router's reach)
1. `schedule_rework` — sets `scheduled_date`/`scheduled_time_window`,
   status → `REWORK_SCHEDULED`. No precondition found (can be called
   regardless of the rework's current status).
2. `start_rework` — status → `REWORK_IN_PROGRESS`. No precondition.
3. `complete_rework` — status → `REWORK_COMPLETED`, sets
   `completed_at`, optionally stores provider notes as
   `customer_visible_notes`. **Conditionally** resolves the parent
   complaint (see `complaint-state-machine.md`).

## Requirements verification

| Requirement | Status |
|---|---|
| A provider complaint route must not directly fabricate a completed rework | Confirmed — no route in `provider_router.py` creates a `ServiceReworkRequest`; only pre-existing requests can be scheduled/started/completed |
| Customer approval must not be impersonated by a provider | Confirmed — no customer-acceptance method for rework was found reachable from this router |
| Rework must preserve tenant and customer ownership | **FIXED THIS SLICE** — previously, `schedule_rework`/`mark_rework_in_progress`/`mark_rework_completed` had **zero** tenant ownership check; any authenticated user of any tenant could manipulate any other tenant's rework request by ID. Fixed via `_get_rework`'s new optional `tenant_id` parameter |
| Rework linkage must not cross Booking/Job/ServiceJob pipelines | Not independently re-traced — `original_job_id`/`job_id` are copied from the parent complaint at creation time (a method not reached by this router); no cross-pipeline adapter was introduced or found in the 3 methods this router does call |
| No cross-pipeline adapter introduced | Confirmed — no new adapter code was written; the fix only added a tenant-ownership check to existing lookups |
| If rework ownership is unresolved, document rather than invent | The creation/approval lifecycle (outside this router) was not investigated — documented as out of scope, not invented |

## Conclusion
Rework is a genuinely separate record type, correctly distinct from
`CustomerComplaint`/`ServiceJob`. The one real defect within this
router's reach (missing tenant ownership check) is fixed. Creation and
admin-approval remain outside this router's boundary and were not
touched.
