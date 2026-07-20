# field_ops Service Bypass Report

## Methods reached by staff_router (6) and the 9 fixed field_ops.router routes

| Method | Ownership check | Bypass found? |
|---|---|---|
| `list_jobs` | tenant/actor filter baked into query (staff/technician forced to `actor_tenant_id`+`actor_id`) | none |
| `get_job` | `_assert_can_access_job` | none |
| `assign_staff` | `_get_job_for_assignment` (tenant_owner own-tenant) | none |
| `accept_job` | `_get_job_for_staff_action` | none |
| `reject_assignment` | `_get_job_for_staff_action` | none |
| `update_status` | `_assert_can_access_job` + job-type guard chain | none |
| `get_job_checklist_items` | `_get_job_for_staff_action` (via caller) | none |
| `start_job_checklist` | `_get_job_for_staff_action` + idempotent provisioning | none |
| `update_job_checklist_item` | `_get_job_for_staff_action` + **new** `CHECKLIST_NOT_ACTIVE` guard | fixed this slice (was missing) |
| `complete_job_checklist` | `_get_job_for_staff_action` + required-item check | none |
| `submit_findings` | `_get_job_for_staff_action` | none |

## Two additional field_ops.router routes inspected during boundary confirmation (not modified)

`update_checklist` (legacy, writes to inert `Job.checklist` JSONB) and `start_checklist` — both
route through the same `_get_job_for_staff_action`/status-guarded methods above; no separate
bypass path exists.

## Conclusion

Every service method reached by this slice's two in-scope routers enforces object ownership
correctly except for the one completion-gate defect (fixed). No further directly-connected
bypass was found. The 19 out-of-scope `field_ops.router` routes (quotes/billing/media/notes/
assessment) were inspected only to confirm they do not share a mutation path with the 15
in-scope routes — see job-note-privacy.md and evidence-media-boundary.md for the two independent
(not shared) findings recorded there.
