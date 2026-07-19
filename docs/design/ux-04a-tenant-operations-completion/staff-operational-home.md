# Staff Operational Home (UX-04A)

New route `/dev/ux-04/staff-home`. Reuses `OperationalActionQueue` (no
duplicate component) with every action's `available` forced to `false` and
a permission-reason string, demonstrating the canonical `staff` role's
permission-limited composition of the exact same queue data shown to
`tenant_owner` on the Command Center page — one component, role-sensitive
data, per the pattern established at UX-04 baseline. No `dispatcher` or
`manager` role/alias appears anywhere in the route, component, or fixture.
