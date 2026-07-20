# field_ops.Job Lifecycle State Machine

`update_status` (in `FieldOpsService`) enforces a job-type-specific guard chain, validated BEFORE
mutation, confirmed correct with no defect:

- CONSULTATION jobs cannot reach `WORK_STARTED`.
- SERVICE jobs cannot reach `ASSESSMENT_STARTED` without `emergency_assessment=true`.
- REPAIR jobs require `QUOTE_APPROVED` before `WORK_STARTED` when `quote_required`.
- SERVICE jobs require `CHECKLIST_COMPLETE` before `WORK_COMPLETE` when `checklist_required`
  (raises `CHECKLIST_REQUIRED_BEFORE_WORK_COMPLETE` otherwise).

This is a distinct state machine from `ServiceJob`/`Booking`'s lifecycle even where transition
names look similar (e.g. "completed"/"in progress") — see job-pipeline-boundary.md. No cross-
pipeline transition logic exists or was added.

## Access to `update_status`

- `field_ops.staff_router.update_status` — staff/technician self-service, gated by
  `require_staff_or_technician_only` + `_get_job_for_staff_action` (assignment check).
- `field_ops.router.update_status` — tenant-side alternate, gated by
  `require_tenant_mutation_permission(P.FIELD_OPS_JOBS_UPDATE)` (fixed this slice from a bare
  `require_permission`, closing an access-scope gap consistent with Slice 2F-13's precedent).

Both call the same `FieldOpsService.update_status`, so the guard chain above applies uniformly
regardless of entry route. See alternate-job-completion-route-audit.md.
