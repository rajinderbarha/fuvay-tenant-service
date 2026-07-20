# My Work Specification

## Grouping logic (built, real, unit-tested)
`src/lib/ux05/myWork.ts` `classifyJob()` buckets every real `Job` into exactly one of
`current | today | upcoming | needs_action | completed`, driven only by real status literals:
- `current`: any in-progress status (`on_the_way`, `reached_site`, `inspection_started`, `inspection_done`,
  `service_started`, `work_done`) -- the technician is actively working this job.
- `needs_action`: `assigned` (accept/reject pending) or `quote_required` (a real status, distinct from "current"
  since no work is happening on it right now).
- `today` / `upcoming`: `accepted`/`scheduled` jobs split by whether `scheduled_date` is today.
- `completed`: `completed`, `cancelled`, `failed`.

`filterJobs()` supports exact-status and needs-action-only filtering. Both are pure functions,
unit-tested in `src/lib/ux05/__tests__/myWork.test.ts` (7 tests, real behavioral assertions on classification
boundaries).

## UI wiring status
**Not yet wired into `JobsListScreen`'s render** this pass -- the screen still uses its pre-existing flat
status-tab filter (`All/Assigned/Active/Completed/Cancelled`). `WorkItemCard` (built this pass, consumes
`MyWorkItemView`) is the intended list-row component once wiring happens. This is a documented gap, not a
silent omission -- see `known-limitations.md`.
