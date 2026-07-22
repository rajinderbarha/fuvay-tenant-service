# Checklist Model Lineage — Slice 2F-13 (Workstream 2)

## Models reached by `checklist_router` (only 2)

| Model | Table | PK | Tenant key | Parent key | Classification |
|---|---|---|---|---|---|
| `ServiceChecklistTemplate` | `service_checklist_templates` | `id` | `tenant_id` | `service_id` (catalog service) | TENANT_CHECKLIST_TEMPLATE |
| `ServiceChecklistItem` | `service_checklist_items` | `id` | (via template) | `template_id` | TENANT_CHECKLIST_TEMPLATE (item) |

`ServiceChecklistItem` fields: `title`, `description`, `sort_order`,
`is_required`, `requires_photo`, `requires_note`, `is_active`,
`deleted_at`. These are **template definitions** — the required/photo/note
flags describe what a future job checklist will demand, not answered
values.

## DISTINCT models NOT reached by this router (documented for the boundary)
| Model | Table | Classification | Where mutated |
|---|---|---|---|
| `JobChecklistItem` | `job_checklist_items` | JOB_CHECKLIST_SNAPSHOT / TECHNICIAN_RESPONSE / COMPLETION_GATE | `field_ops.service.py` (FieldOpsService), `field_ops.staff_router` — **out of scope** |
| `Job` | `jobs` | (field_ops job pipeline, NOT ServiceJob) | `field_ops.router.py` / service |
| `JobMedia` | `job_media` | EVIDENCE_OR_MEDIA | field_ops job surface (out of scope) |
| `JobQuote` | `job_quotes` | QUOTE_CHECKLIST-adjacent | field_ops quote surface (out of scope) |

`JobChecklistItem` carries its OWN `is_required`/`requires_photo` columns
(copied from the template at job-checklist-seed time) plus `job_id` and
`tenant_id` — it is a materialized snapshot, independent of the template
rows this router manages.

## Not present anywhere (confirmed absent, not assumed)
No `ChecklistTemplateVersion`, `ChecklistApproval`, `ChecklistEvidence`,
`InspectionChecklist`, or `CompletionChecklist` model exists — the module
has no template-versioning model, no separate approval model, and no
evidence model (photo requirements are boolean flags; the actual photo
storage is `JobMedia`, on the out-of-scope job surface).

## No model merge
`ServiceChecklistTemplate`/`Item` (this router) and `JobChecklistItem`
(job surface) are kept strictly distinct — no adapter, no shared table.
