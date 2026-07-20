# Job Pipeline Boundary — Slice 2F-13 (Workstream 3/12, IMPORTANT JOB-PIPELINE RULE)

## Exact linked record: NONE from this router
`checklist_router` operates on `ServiceChecklistTemplate` (keyed to a
catalog `service_id`) and `ServiceChecklistItem` (keyed to `template_id`).
**Neither references a job.** No route in this router reads or mutates
`Job`, `ServiceJob`, `Booking`, `ServiceBooking`, or `JobChecklistItem`.
Confirmed by direct source read of `checklist_router.py` and
`checklist_template_service.py` (no `Job*` import).

## The job pipeline this MODULE (field_ops) uses elsewhere
`field_ops.models.Job` (`jobs` table) — the field-ops job pipeline —
**distinct from `ServiceJob`**. The per-job checklist snapshot
`JobChecklistItem` (`job_checklist_items`) links to `field_ops.Job.job_id`
and is seeded from `ServiceChecklistTemplate` at job-checklist-start time
by `FieldOpsService` / `BookingService` (see `test_checklist_system.py`).
That seeding + completion gating is **out of scope** (lives in
`field_ops.service.py` / `staff_router`).

## Completion gating (documented boundary, not modified)
Existing tests (`test_checklist_system.py::test_seeded_checklist_blocks_
work_complete_until_done`) show `field_ops.Job` work-completion IS gated
by its `JobChecklistItem` snapshot — but that gate lives in the job
execution service, NOT in this template router. This router's template
mutations have **no** job-lifecycle effect: `delete_template` explicitly
documents "historical job_checklist_items are never touched." So a
template change cannot retroactively alter or bypass any job's completion
gate.

## No adapter introduced
No Booking↔ServiceBooking or Job↔ServiceJob adapter was created. No
checklist record was transferred across pipelines. `field_ops.Job` and
`ServiceJob` remain separate. PartsRequest ownership unchanged.
