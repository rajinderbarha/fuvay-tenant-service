# UX-03 Tenant Portal — Implementation Summary

## Mode

**Mode B** — `npm install` retried once (bounded), failed identically to a
prior attempt outside this task (`ERR_SSL_CIPHER_OPERATION_FAILED` +
Windows AV-lock cleanup errors). No `tsc`/`vitest`/`next build` executed
for tenant-portal, design-system, or super-admin. See execution-mode.md,
environment-blocker-report.md, build-report.md, frontend-test-report.md —
none of these claim a passing run.

## What was built (source-level only)

- **Types & fixtures**: `lib/ux03/types.ts` (16 entity interfaces + a
  `Ux03DataAdapter`), `lib/ux03/fixtures.ts` (realistic home_services
  fixture data + a fixture-backed adapter implementation), real
  `permission_key` strings sourced from `app/core/permissions.py`.
- **Information architecture**: `lib/ux03/nav-ia.ts` — 17 nav groups
  extending `TENANT_NAV_GROUPS`, not wired into production layout (mirrors
  UX-02 precedent; see product-decisions-required.md).
- **Reusable patterns** (`components/ux03/patterns/`): TenantListPage,
  TenantDetailPage, SetupWizard, OperationalWorkspace.
- **Widgets** (`components/ux03/widgets/`): ReadinessTag, PipelineBadge,
  ReviewStateBanner, PermissionEditor, TeamMemberDetail (unified
  staff/technician pattern).
- **Dev showcase**: 25 routes under `app/dev/ux-03/**` covering dashboard
  (pre-approval/approved), setup wizard, profile review states, team
  list/detail/permissions, booking/job lists+detail, dispatch, parts
  approval, package/credits, finance history, security deposit, pricing,
  service areas, customers/complaints, compliance, media, settings, audit,
  read-only/restricted.
- **Tests written (not executed)**: 4 files, 13 `it()` cases covering
  canonical-role enforcement, StaffPermission deny-precedence, pipeline
  separation, ServiceJob-only parts, and pattern behavior.
- **Shared design-system change**: one additive `statusRegistry` extension
  in `frontend/packages/design-system/src/tokens/motion.ts`, verified
  (grep-based) not to affect any Super Admin `StatusBadge` usage.
- **Route audit**: 84 existing tenant-portal routes cross-referenced
  against `nav-config.ts`, producing a duplication map (11 concept
  clusters) and an orphaned/broken-nav report — naming/config depth, not a
  full per-file manual read.
- **66 documentation files** under `docs/design/ux-03-tenant-portal/`
  (see artifact-manifest.csv).

## Hard constraints honored

- Zero changes to `app/`, `tests/`, `scripts/`, `migrations/` (verified:
  `git diff --stat 8953a84..HEAD` on those paths is empty).
- Zero changes to `frontend/super-admin/`, `frontend/customer-app/`,
  `mobile/customer-app/`, `mobile/staff-app/` (same verification).
- Only `tenant_owner`/`staff`/`technician` ever appear as a role
  (`nav-ia.test.ts` asserts no invented role name appears anywhere in
  `UX03_NAV_GROUPS`).
- Booking (field_ops.Job) vs ServiceJob pipelines kept distinct via
  `PipelineBadge` everywhere; PartsRequest is ServiceJob-only with no
  technician install authority; package credit / commission / security
  deposit rendered as three separate concepts; no payout/withdrawal UI;
  cancel/reschedule presented as unresolved on both pipelines; geo
  mutations default to read-only pending the frozen-slice decision.
- No raw hex colors in feature components (all colors are
  `var(--design-token)` references).
- No duplicate status registry — one additive extension to UX-01's.

## Incident during this session (self-corrected)

Partway through, an external process on this shared machine switched
`/g/serviceos`'s checked-out branch to `master` twice while this task was
mid-flight, causing several commits to land on `master` momentarily. Both
times this was caught immediately (branch verification after committing),
the commits were cherry-picked onto `design/ux-03-tenant-portal`, and
`master` was reset back to its rightful commit (`50840ac`) with no data
loss and no stray commits left on `master`. No backend files were affected
by this incident.

## Known gaps

See known-limitations.md, deferred-items.md, product-decisions-required.md.
Chief among them: nothing in this phase has run through a real
TypeScript/test/build pipeline, and several duplicate-route concepts
(catalog, service areas, job/booking short-paths, staff roster, wallet)
still need a product decision before consolidation.
