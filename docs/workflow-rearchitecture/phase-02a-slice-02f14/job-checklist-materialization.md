# Job Checklist Materialization

`JobChecklistItem` rows are materialized (copied) from Slice 2F-13's
`ServiceChecklistTemplate`/`ServiceChecklistItem` at job-checklist-start time via
`_provision_job_checklist_items`, looked up tenant-scoped via `job.tenant_id` + `job.service_id`.

Confirmed an immutable, job-scoped execution snapshot: template edits made after provisioning do
not retroactively change already-provisioned `JobChecklistItem` rows (fields: `job_id`,
`tenant_id`, `template_item_id`, `title`, `description`, `sort_order`, `is_required`,
`requires_photo`, `requires_note`, `is_completed`, `completed_by_staff_id`, `completed_at`,
`notes`, `photo_urls`).

## Idempotency (duplicate-generation-safe)

`_provision_job_checklist_items` guards re-provisioning with
`if not existing.scalars().first(): ...` — calling `start_job_checklist` twice on the same job
does not create duplicate `JobChecklistItem` rows. See duplicate-concurrency-review.md.
