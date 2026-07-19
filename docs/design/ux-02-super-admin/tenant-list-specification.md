# Tenant List Specification

Component: `EnterpriseListPage<TenantFixture>` instantiated in
`app/dev/ux-02/tenants/page.tsx`. Readiness: `READ_ONLY_READY` (tenant data itself is a real,
confirmed backend capability — `admin_catalog/tenant_service` — but bulk actions here are
design-only).

## Columns
Tenant (name, links to Tenant 360), Vertical, Status (StatusBadge), Plan, Package Credit
(right-aligned, currency), Risk (dot badge), City/Region.

## Filters
Vertical (home_services / real_estate / coaching), Status (active / suspended /
pending_verification / onboarding / deactivated). Applied-vs-draft chip presentation per
`filter-saved-view-system.md`.

## Search
Client-side substring match over `displayName + ownerName + city` (fixture-scale only; a real
implementation would push search server-side).

## Bulk actions
"Suspend selected", "Export selected" — both design-only impact-preview + confirmation, no backend
mutation. See `bulk-action-pattern.md`.

## Mobile
Below breakpoint, rows render as `mobileCard` (name + status + city/plan) instead of the table —
see `responsive-super-admin-behavior.md`.

## Not yet built
Column manager / saved views persistence — MOCK only, not implemented as a working persistence
layer (see `filter-saved-view-system.md`).
