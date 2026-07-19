# Booking Detail Specification (types built, showcase route DEFERRED)

Type: `BookingDetailView` (`lib/ux04/types.ts`) — `booking`
(`BookingFixture`), `sla`, `timeline` (`AuditEventFixture[]`),
`jobTransition` (`BookingToJobTransitionView | null`), `actions`.

No dedicated `/dev/ux-04/booking-detail` route was built this pass (the
Job Detail Workspace route demonstrates the equivalent pattern for the
ServiceJob pipeline; the Booking-pipeline variant reuses the same section
layout by design but wasn't wired into its own showcase page). Preserves
source-pipeline info via `PipelineBadge` + `booking.canonicalId`, same as
every other UX-04 view. No cancel/reschedule action is modeled anywhere —
`cancelSupported: "unresolved_mock_only"` is carried through unchanged
from the UX-03 fixture.
