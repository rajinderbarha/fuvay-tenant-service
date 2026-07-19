# Staff Operational Home (DEFERRED — no dedicated route)

No dedicated staff-operational-home showcase route was built this pass.
The Command Center route (`app/dev/ux-04/command-center`) already
demonstrates the permission-filtering pattern this page would need
(`ActionPermissionView.available` gating per item) — a staff-scoped
variant would reuse `OperationalActionQueue` with a queue pre-filtered to
that staff member's assigned work plus permission-gated shared queues
(unassigned bookings, quote review, parts approval, checklist review,
customer issues, SLA risks, low-credit-if-finance-access). No new
component or type is required to build it; it is a composition exercise
on top of what already exists. Never includes tenant-owner-only settings,
finance without permission, StaffPermission management without
permission, or platform-admin surfaces — and never invents a
`tenant_manager`-style persona.
