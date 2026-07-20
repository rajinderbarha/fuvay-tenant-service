# Alternate Job-Completion Route Audit

## Question

Can any route other than `complete_job_checklist` + `update_status`'s `WORK_COMPLETE` transition
reach a completed state without satisfying the required-item completion gate?

## Routes reaching `FieldOpsService.update_status` / `complete_job_checklist`

| Route | Router | Guard (this slice) |
|---|---|---|
| `PUT /v1/staff/me/jobs/{id}/status` | staff_router | `require_staff_or_technician_only` + `_get_job_for_staff_action` |
| `POST /v1/staff/me/jobs/{id}/checklist/complete` | staff_router | same |
| `PUT /v1/jobs/{id}/status` | field_ops.router | `require_tenant_mutation_permission(FIELD_OPS_JOBS_UPDATE)` (fixed this slice) |
| `POST /v1/jobs/{id}/checklist/complete` | field_ops.router | `require_staff_or_technician_only` (fixed this slice) |

Both routers call the identical `FieldOpsService` methods, so the same gate logic
(required-item-completion-gate.md) applies regardless of entry point — there is no alternate
implementation of either method.

## Legacy `Job.checklist` JSONB path

`update_checklist` (legacy route on both routers) writes only to the inert `Job.checklist` JSONB
field (see field-ops-model-lineage.md). `update_status`'s guard checks
`job.checklist_required` + `JS.CHECKLIST_COMPLETE` (the normalized path) for jobs with
`checklist_required=True` — it does not consult `Job.checklist` for the gate decision. Confirmed
no bypass: a technician writing to the legacy JSONB field cannot advance `job.status` to
`CHECKLIST_COMPLETE`, since that transition is only set by `complete_job_checklist`'s own
required-item check against `JobChecklistItem`.

## Conclusion

No alternate route bypasses the authoritative completion gate. `close_job`,
`financial_close`, `generate_invoice` (out-of-scope routes) were inspected for a direct
`WORK_COMPLETE`-skipping path and found to operate downstream of, not instead of, `update_status`
(each begins by loading the job and checking its current `status`, not by setting it directly to
a completed state without validation) — no defect found in that inspection, and no changes were
made to those out-of-scope routes.
