# Job List Specification

Built as part of `app/dev/ux-04/booking-list/page.tsx` (job rows within the
combined table) — type `JobListItemView`.

Presets specified (Active/Unassigned/On the way/Inspection/In
progress/Awaiting parts/Work done/Awaiting completion/Completed/SLA risk)
are **not implemented as filter controls this pass** — same deferral as
booking-list-specification.md. `job.status` and `sla.state` carry every
value a real preset filter needs.

Note: the real `ServiceJob` status vocabulary in the reused UX-03 fixture
type (`quoted | scheduled | in_progress | awaiting_parts | completed |
cancelled`) is narrower than the full lifecycle referenced in the UX-04
brief (assigned/on_the_way/inspection/in_progress/work_done/completed) —
this phase did not re-verify the literal enum in
`app/engines/home_service_assignment/models.py` /
`app/engines/execution/models.py` against the brief's richer list; treat
the richer lifecycle names in `JobStatusTimeline`'s usage as illustrative
until confirmed against the real model (see
`backend-contract-dependencies.csv`).
