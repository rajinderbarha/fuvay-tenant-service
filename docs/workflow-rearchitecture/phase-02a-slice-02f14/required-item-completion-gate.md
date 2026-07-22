# Required-Item Completion Gate

Classified `AUTHORITATIVE_JOB_COMPLETION_GATE` — a dual gate:

1. **Item level**: `complete_job_checklist` requires `job.status == JS.CHECKLIST_STARTED` and
   that every `is_required` `JobChecklistItem` has `is_completed == True`; raises
   `CHECKLIST_NOT_COMPLETE` otherwise.
2. **Job level**: `update_status`'s `WORK_COMPLETE` transition requires
   `job.status == JS.CHECKLIST_COMPLETE` whenever `job.checklist_required is True`; raises
   `CHECKLIST_REQUIRED_BEFORE_WORK_COMPLETE` otherwise.

## Defect found and fixed this slice

`update_job_checklist_item` had **no state guard at all** prior to this slice: a technician could
call `PUT /v1/staff/me/jobs/{job_id}/checklist/items/{item_id}` after `complete_job_checklist` had
already finalized the checklist (job at `CHECKLIST_COMPLETE`, or further progressed to e.g.
`WORK_COMPLETE`), silently un-completing a previously-required item with no re-validation of
either gate above. This would let an already-passed completion gate be quietly invalidated after
the fact without anyone noticing.

**Fix**: `update_job_checklist_item` now requires `job.status == JS.CHECKLIST_STARTED` (raises
`CHECKLIST_NOT_ACTIVE`, 422, otherwise) — mirroring `complete_job_checklist`'s own existing
precondition rather than inventing a new gate. Item mutation is only meaningful while the
checklist is actively being worked.

Verified via `TestChecklistItemCompletionGateIntegrity` in
`tests/test_phase2f14_field_ops_staff_authorization.py`:
`test_cannot_mutate_item_after_checklist_complete`,
`test_cannot_mutate_item_after_job_moved_past_checklist`,
`test_mutation_allowed_while_checklist_started`, `test_foreign_job_item_rejected`.
