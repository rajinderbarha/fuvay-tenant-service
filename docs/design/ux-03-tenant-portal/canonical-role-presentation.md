# Canonical Role Presentation

Only three tenant-side roles exist and may ever be presented as a role in
this portal: `tenant_owner`, `staff`, `technician`. Confirmed against
`app/core/permissions.py::ROLE_PERMISSIONS` keys.

Job titles (e.g. "Branch Manager", "Dispatcher", "Office Coordinator") are
free-text descriptive labels a tenant assigns to a team member
(`TeamMemberFixture.jobTitle`) — they carry no authorization meaning and
must never be used in a permission check or nav-visibility rule. The UI
renders both the canonical role badge and the descriptive title side by
side (see `TeamMemberDetail.tsx`) with a tooltip clarifying the distinction.

`app/core/permissions.py` notes that `"technician"` is the role value
actually seeded onto real staff/technician accounts in production, and its
`ROLE_PERMISSIONS` entry deliberately mirrors `"staff"` exactly — the UI
never assumes technician capability differs from staff except via
`StaffPermission` overrides (see `staffpermission-presentation.md`).

Never invent: `tenant_manager`, `tenant_readonly`, `office_staff`,
`business_admin`, `branch_manager`, `dispatcher`, `accountant`, or any other
role-shaped string. `nav-ia.test.ts` asserts none of these strings appear in
`UX03_NAV_GROUPS`.
