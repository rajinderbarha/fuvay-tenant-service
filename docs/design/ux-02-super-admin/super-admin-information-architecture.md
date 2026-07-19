# Super Admin Information Architecture (UX-02)

Defined in `frontend/super-admin/lib/ux02/nav-ia.ts` as `UX02_NAV_GROUPS`, extending the existing
`NavItem`/`NavGroup` shape from `lib/nav-config.ts` (see compatibility report — not wired into
production layout by this phase; see `product-decisions-required.md`).

## Groups
Overview, Tenants, Operations, Catalog & Serviceability, Commerce & Finance, Trust & Compliance,
Security, Platform Configuration, Audit & Monitoring, Support.

## Per-item fields (`Ux02NavItem`)
`label`, `description`, `href`, `parent group`, `canonicalRoles: CanonicalAdminRole[]`,
`backendCapability` (free-text pointer, not a contract guarantee), `readiness: ReadinessState`,
`readOnlyBehavior` (`hidden` | `visible_disabled` | `visible_read_only_view`), `badge`
(`new`|`attention`|`none`), `mobileBehavior` (`full`|`collapsed_summary`|`hidden_on_mobile`).

## Canonical roles
Only `super_admin`, `admin_operations`, `admin_finance`, `admin_security`, `admin_readonly` appear
anywhere in `canonicalRoles`. No other role name is used in this phase.

## Governance note (repeated per hard constraint)
`canonicalRoles`/nav visibility is a UX convenience only — it is never an authorization boundary.
Real access control is enforced server-side (`app.core.permissions.ROLE_PERMISSIONS`), independent
of whether a nav item is rendered. See `design-governance-rules.md`.

See `super-admin-navigation-map.csv` for the full flattened per-item table.
