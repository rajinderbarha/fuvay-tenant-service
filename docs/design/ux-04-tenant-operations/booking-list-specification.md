# Booking List Specification

Built: `app/dev/ux-04/booking-list/page.tsx` (combined booking+job list
showcase — renders both `BookingListItemView` and `JobListItemView` rows
in one table, each keeping its own `PipelineBadge`).

Columns shown: pipeline badge, customer, service, status (`StatusBadge`,
pipeline-literal values, never merged), SLA (`SLAIndicator`), next action.

Presets specified (Today/Unassigned/Upcoming/Needs quote/SLA
risk/Completed/Cancelled-where-real) are **not implemented as filter
controls this pass** — the showcase renders the full fixture list
unfiltered. `BookingListItemView`/`JobListItemView` carry every field a
real filter would need (`status`, `sla.state`, `scheduledAt`,
`assignedStaffId`/`assignedTechnicianId`), so adding filter chips is a
follow-up UI task, not a data-model gap.

Pipeline-specific actions only: `BookingListItemView.actions` and
`JobListItemView.actions` are independent `ActionPermissionView[]` — a
booking row never gets a job-only action (e.g. quote/checklist/parts) and
vice versa.
