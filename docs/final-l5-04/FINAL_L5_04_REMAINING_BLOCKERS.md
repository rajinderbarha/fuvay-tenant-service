# FINAL-L5-04 — Remaining Blockers

## Blocker 1 (P0, the central finding of this sprint): Tenant entitlement is not enforced in navigation, frontend or backend
- **What**: `tenant.category_id` is NULL for every seeded tenant. `TENANT_NAV_GROUPS` is 100% static with no entitlement filtering consumed. `get_dashboard_runtime`/`get_navigation` in `portal_router.py` either depend on the always-null `category_id` or fall back to a static `_NAV_BY_DASHBOARD_TYPE` lookup, not real per-tenant module/category entitlement.
- **Impact**: Every tenant user sees every tenant nav item and can reach every corresponding backend route, regardless of what modules/verticals that tenant actually purchased/enabled.
- **Why not fixed this sprint**: The fix requires extending the `vertical`-column fallback pattern (already proven safe for the analogous `category_type` field in an earlier sprint) to `enabled_engines`/`modules` resolution, then wiring `TenantLayout` to filter by it, then re-running the same live browser-verification rigor used for the admin-side vertical fix this sprint. This is real, scoped, plausible near-term work — not attempted blind this sprint because a wrong fix here would regress live navigation for every real tenant, and the dedicated backend verification this deserves didn't fit this sprint's time budget.
- **Recommended next step**: (1) extend the `category_type` fallback pattern to `enabled_engines`/`modules`, (2) add entitlement filtering to `TENANT_NAV_GROUPS` rendering in `TenantLayout.tsx`, (3) add backend-side entitlement enforcement to tenant-scoped routes (not frontend-hiding alone), (4) browser-certify with the same before/after live-toggle pattern used in this sprint's `final-l5-04-admin-category-nav.spec.ts`.

## Blocker 2 (P2): No responsive/mobile navigation
- **What**: No breakpoint logic exists in either layout; sidebar is a fixed-width desktop-only design.
- **Impact**: Usability degradation below ~1024px viewport width, not a data/security issue.
- **Recommended next step**: dedicated UI sprint to add an off-canvas/hamburger pattern reading from the same `NAV_GROUPS`/`TENANT_NAV_GROUPS` source (must not introduce a second nav config).

## Blocker 3 (P3): Missing `aria-current="page"` on active sidebar items
- **What**: Active state is conveyed visually (background color) only, not to assistive technology.
- **Impact**: Screen-reader users cannot determine current page from the nav alone.
- **Recommended next step**: one-line addition to `SidebarItem` in both layouts: `aria-current={active ? "page" : undefined}`.

## Blocker 4 (P3): Sparse `page-registry.ts` coverage
- **What**: Only ~55 of 144 super-admin routes and a similarly partial fraction of ~95 tenant-portal routes have breadcrumb metadata.
- **Impact**: Most pages show no breadcrumb (safe default, not broken, but incomplete).
- **Recommended next step**: pure data-entry task, low risk, no logic change — expand registry coverage incrementally.

## Blocker 5 (P3): Governance nav group and several mission-specified rule-configuration pages not confirmed to exist or be linked
- **What**: Roles/Permissions pages exist but are unlinked; a dedicated "Governance" group doesn't exist; several specific rule-config pages (Health Rules, Badge Rules, etc.) were not individually verified this sprint.
- **Recommended next step**: dedicated per-item audit across the full route inventory, then either link existing pages or build missing ones.

## Not a blocker (re-confirmed working, listed for completeness)
- Admin-side dynamic vertical/category visibility: real and live (this sprint's fix).
- Breadcrumbs: real and live (this sprint's fix).
- Auth/role/tenant-scope guards on the backend: real, tested, unaffected by this sprint.
- 0 duplicate route/menu IDs in the generated registry.

## Result
1 P0 blocker (tenant entitlement) prevents a clean `READY_FINAL_L5_04_DYNAMIC_NAVIGATION_CERTIFIED`. 4 lower-severity gaps documented with concrete next steps. See Final Report for the resulting recommendation.
