# Team Management Specification

Unified area (`/dev/ux-03/team-list` -> `TenantListPage`): all members
(owner/staff/technicians/invitations/inactive) in one searchable list,
filterable by status and role. Detail view uses the single
`TeamMemberDetail` pattern for both staff and technician (see
team-member-detail-pattern.md). Permission editing is owner-only
(`ux03-team-permissions` nav item, canonicalRoles: `["tenant_owner"]`).
