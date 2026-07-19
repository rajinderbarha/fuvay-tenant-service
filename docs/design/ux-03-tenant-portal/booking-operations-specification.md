# Booking Operations Specification

Booking -> field_ops.Job pipeline. List (`/dev/ux-03/booking-list`) and
detail preserve `canonicalId` (the real `field_ops.Job` id) via
`PipelineBadge` on every row. Statuses: requested, confirmed, in_progress,
completed, cancelled. Cancel/reschedule actions are NOT rendered as working
controls — `cancelSupported: "unresolved_mock_only"` on every fixture row,
per the task's product-unresolved constraint.
