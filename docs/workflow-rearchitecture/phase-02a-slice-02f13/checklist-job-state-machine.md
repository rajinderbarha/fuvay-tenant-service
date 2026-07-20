# Checklist / Job State Machine — Slice 2F-13 (Workstream 12)

## Template lifecycle (this router's only state)
`ServiceChecklistTemplate` / `ServiceChecklistItem` have a minimal
lifecycle: `is_active` (bool) + `deleted_at` (soft delete). There is no
multi-state checklist status machine in this router.
- Create → active.
- Update → fields changed (stays active unless `is_active` toggled).
- Delete → `is_active=False`, `deleted_at` set (soft). Deleted templates
  are excluded from all reads (`deleted_at.is_(None)` filter) and from
  `_get_template_for_tenant` (raises NOT_FOUND).
- A soft-deleted template/item cannot be further mutated
  (`_get_template_for_tenant` / `_get_item_for_template` reject
  `deleted_at is not None`).

## Job state machine (out of scope, documented boundary)
The `field_ops.Job` lifecycle and its `JobChecklistItem`-gated
work-completion are on the out-of-scope job-execution surface
(`field_ops.service.py`/`staff_router`), NOT this router. No checklist
mutation here changes any job status; template and job statuses cannot
become contradictory because template edits never propagate to job
snapshots.

## No booking-pipeline adapter
No Booking/ServiceBooking/Job/ServiceJob adapter introduced. `field_ops.Job`
remains distinct from `ServiceJob`.
