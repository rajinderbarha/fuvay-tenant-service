# Home Recomposition (Technician)

`HomeScreen` (extended in place) now derives its "Active Job", "Needs Your Action", and "Today's Schedule"
sections from the same real, tested `groupJobs()` (`src/lib/ux05/myWork.ts`) that `JobsListScreen`'s My Work tabs
use — replacing its own separate, slightly different `ACTIVE_STATUSES` filter. This closes a real
consistency gap: before this round, "active job" on Home and "Active" tab on Jobs could theoretically disagree
about which job counted as current (two independently-maintained status lists); now there is exactly one
classification function both screens call.

New section: **Needs Your Action** — jobs in `groupJobs().needs_action` (`assigned` awaiting accept/reject,
`quote_required`) rendered above the schedule list with a distinct warning-colored left border, so a technician
sees required decisions before browsing today's plan.

**Pending parts & checklist progress** (workstream 4's remaining two priorities) are rendered as a single
honestly-labeled `MOCK_DESIGN_ONLY` placeholder line — no live per-job parts-summary or checklist-progress
aggregation endpoint exists to compute a real count across all of a technician's jobs (each job's own checklist
progress, where it exists at all, is per-job local state in the Inspection/Checklist showcase, not aggregated
anywhere).
