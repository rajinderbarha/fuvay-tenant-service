# Job Checklist Item Ownership

`JobChecklistItem` rows carry `job_id` + `tenant_id` directly (denormalized from the parent
`Job` at materialization time — see job-checklist-materialization.md).

## Enforcement

- Item reads/writes are always reached through a job first: every route
  (`my_job_checklist`, `my_job_checklist_start`, `my_job_checklist_item`,
  `my_job_checklist_complete` on staff_router; their equivalents on `field_ops.router`) loads and
  authorizes the parent `Job` via `_get_job_for_staff_action` before touching any
  `JobChecklistItem` row.
- `update_job_checklist_item` additionally verifies `item.job_id == job.id` after loading the
  item by `item_id` — `if not item or item.job_id != job.id: raise
  ServiceOSException("CHECKLIST_ITEM_NOT_FOUND", ..., status_code=404)`. This prevents a
  technician assigned to job A from mutating a `JobChecklistItem` belonging to job B even if they
  correctly resolve their own job A first and then guess a foreign `item_id` (cross-item IDOR).

## Verification

`test_foreign_job_item_rejected` in
`tests/test_phase2f14_field_ops_staff_authorization.py::TestChecklistItemCompletionGateIntegrity`
confirms a technician assigned to job A cannot mutate an item belonging to job B (404).
