# field_ops Model Lineage

| Model | Table | Scope | Role |
|---|---|---|---|
| `Job` | `jobs` | tenant + assigned staff | primary lifecycle record for this slice |
| `JobStatusHistory` | `job_status_history` | per-Job | audit trail of `update_status` transitions |
| `JobNote` | `job_notes` | per-Job | see job-note-privacy.md |
| `JobMedia` | `job_media` | per-Job | see evidence-media-boundary.md |
| `JobQuote` | `job_quotes` | per-Job | out of scope (billing/quotes capability) |
| `JobChecklistItem` | `job_checklist_items` | per-Job, materialized snapshot | see job-checklist-materialization.md |

## Legacy inert field

`Job.checklist` (JSONB: `list[{"step": str, "completed": bool}]`) is mutated only by the legacy
`FieldOpsService.update_checklist()` method (exposed at `field_ops.router`'s deprecated
`update_checklist` route, now behind `require_staff_or_technician_only`). Confirmed DEAD/INERT
for jobs using the normalized `JobChecklistItem` system: `update_status`'s own inline guard
`if job.checklist and not all(...)` is a no-op when the field is empty/falsy, which it always is
for jobs provisioned via `_provision_job_checklist_items`. Not a bypass — see
required-item-completion-gate.md and alternate-job-completion-route-audit.md.

## Confirmed NOT part of this lineage

`ServiceJob`, `ServiceBooking`, `Booking`, `PartsRequest`, `ServiceChecklistTemplate`,
`ServiceChecklistItem`, `quote_checklist`. See job-pipeline-boundary.md.
