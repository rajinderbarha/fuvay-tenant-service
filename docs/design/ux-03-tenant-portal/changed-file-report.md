# Changed File Report

Full list of files touched by this phase (`git diff --name-only
8953a84..HEAD -- frontend/tenant-portal frontend/packages
docs/design/ux-03-tenant-portal`):

- 1 shared design-system file: `frontend/packages/design-system/src/tokens/motion.ts` (additive statusRegistry keys only)
- `frontend/tenant-portal/lib/ux03/*` — types, fixtures, nav-ia, tests
- `frontend/tenant-portal/components/ux03/patterns/*` — TenantListPage, TenantDetailPage, SetupWizard, OperationalWorkspace
- `frontend/tenant-portal/components/ux03/widgets/*` — ReadinessTag, PipelineBadge, ReviewStateBanner, PermissionEditor, TeamMemberDetail
- `frontend/tenant-portal/components/ux03/__tests__/*`
- `frontend/tenant-portal/app/dev/ux-03/**` — 20 dev-showcase routes + index
- `docs/design/ux-03-tenant-portal/**` — this documentation set

No file under `app/`, `tests/`, `scripts/`, `migrations/`,
`frontend/super-admin/`, `frontend/customer-app/`, `mobile/customer-app/`,
or `mobile/staff-app/` was changed — see `backend-non-change-report.md` and
`super-admin-non-regression-report.md`.
