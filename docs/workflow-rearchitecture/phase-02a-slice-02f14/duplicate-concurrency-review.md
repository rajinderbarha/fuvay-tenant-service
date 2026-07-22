# Duplicate / Concurrency Review

- **`_provision_job_checklist_items`** — idempotent. Guarded by
  `if not existing.scalars().first(): ...` before inserting `JobChecklistItem` rows; calling
  `start_job_checklist` twice on the same job does not duplicate rows.
- **`complete_job_checklist`** — re-invoking after the checklist is already `CHECKLIST_COMPLETE`
  re-checks `job.status == JS.CHECKLIST_STARTED` and raises rather than silently re-finalizing;
  not a duplicate-completion vector.
- **`update_job_checklist_item`** (fixed this slice) — the new `CHECKLIST_NOT_ACTIVE` guard also
  closes a duplicate-mutation vector: repeated calls after finalization are now uniformly
  rejected regardless of how many times attempted.
- **`accept_job`/`reject_assignment`** — both call `_get_job_for_staff_action`, which re-checks
  current job status implicitly via the status-history write path; repeated accept calls after
  the job has moved past `ASSIGNED` are rejected by `update_status`'s own transition validation
  (not specifically re-tested this slice beyond the existing lifecycle guard chain, which was
  confirmed correct in job-lifecycle-state-machine.md).

No new duplicate/concurrency defect was found beyond the completion-gate integrity issue already
documented in required-item-completion-gate.md.
