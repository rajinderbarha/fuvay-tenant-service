# Canonical Admin Role Presentation

Only five roles are ever used in UX-02 UI code, fixtures, or docs:
`super_admin`, `admin_operations`, `admin_finance`, `admin_security`, `admin_readonly`.

## How each role shapes presentation (not access control)
- **super_admin** — sees every dashboard widget group (finance + security + ops); full nav.
- **admin_operations** — sees ops/tenant/catalog widgets; finance and security widgets hidden from
  the dashboard composition (`components/ux02/widgets/RoleDashboard.tsx`) but nav items for those
  areas may still render `visible_disabled`/`visible_read_only_view` depending on `readOnlyBehavior`.
- **admin_finance** — sees finance widgets (package credit, commission) in addition to the
  cross-role snapshot; does not see the Security "Risk Overview" section.
- **admin_security** — sees the Risk Overview / security-observations section; does not see the
  finance widgets.
- **admin_readonly** — sees the same composed dashboard as other roles but every list/detail/review
  pattern renders in its read-only mode (`readOnlyBehavior: visible_read_only_view` — no bulk actions,
  no decision panel mutations).

## Implementation
One dashboard component (`RoleDashboard`) branches internally on `role` to show/hide sections —
explicitly NOT five separate dashboard components, per the task spec. Same pattern applies to
`EnterpriseListPage`/`EnterpriseDetailPage`/`ReviewApprovalWorkspace`: role and readiness are props,
not forked components.

## Restated governance rule
Role-based nav/dashboard visibility is presentation only. It never substitutes for backend
authorization — every canonical role's real permissions come from the server.
