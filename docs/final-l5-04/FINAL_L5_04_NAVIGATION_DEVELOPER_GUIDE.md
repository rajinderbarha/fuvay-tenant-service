# FINAL-L5-04 — Navigation Developer Guide

This documents the *real, current* navigation architecture as it exists after this sprint — not an idealized target architecture.

## Super Admin (`frontend/super-admin`)
- **Static nav**: `NAV_GROUPS` array inside `AdminLayout.tsx` — 9 groups, 44 items, hand-maintained. To add a page to the sidebar, add an entry here (`{id, label, href, icon?, group}`).
- **Dynamic vertical nav**: `VerticalCatalogSection` inside `AdminLayout.tsx`, driven by `verticalCatalogApi.getEffectiveMenu()` → `app/engines/vertical_catalog/service.py::get_effective_menu()`. This is live-queried on every mount and does **not** need a manual sidebar entry per vertical — new verticals seeded on the backend appear automatically once enabled.
- **Live-refresh after mutation** (added this sprint): if you build a page that enables/disables/activates/deactivates a vertical or category, call `useAdminMenuRefresh()` (exported from `AdminLayout.tsx`) and invoke the returned function immediately after your mutation succeeds, so the sidebar updates without requiring a page reload. See `app/admin/verticals/page.tsx` and `app/admin/categories/page.tsx` for the reference pattern.
- **Breadcrumbs** (wired this sprint): add an entry to `lib/page-registry.ts`'s `resolvePageMeta` map for your route with a `breadcrumbs: [...]` array of 2+ items to get an automatic breadcrumb trail. 1-item arrays render nothing by design.
- **Active state**: pass `activeNav="<nav-item-id>"` to `<AdminLayout>` from your page component; it is compared against `NavItem.id`, not the URL, so it must match exactly.

## Tenant Portal (`frontend/tenant-portal`, includes `/staff/*` technician routes — there is no separate staff app)
- **Static nav**: `TENANT_NAV_GROUPS` in `lib/nav-config.ts` — 7 groups, 25 items, 100% static, no entitlement filtering currently applied (see Remaining Blockers).
- **Breadcrumbs** (wired this sprint): same pattern as above via `lib/page-registry.ts`'s `resolveTenantPageMeta`.
- **Known limitation — do not assume module/category filtering exists**: `NavItem.permission` is declared in the interface but is **not consumed** anywhere for filtering. Do not build a feature that assumes hiding a tenant nav item by entitlement already works — it doesn't, on either the frontend or the backend, because `tenant.category_id` is always NULL (see Remaining Blockers for the fix path).

## Adding a new page, in general
1. Create the route/page component.
2. Add a nav entry to the relevant static array (`NAV_GROUPS` or `TENANT_NAV_GROUPS`) if it should appear in the sidebar — pages intentionally left out of the sidebar (detail/wizard pages) should stay contextual (linked from their parent list page), not added here.
3. Add a `page-registry.ts` entry with 2+ breadcrumb items if you want a breadcrumb trail.
4. Ensure the backend route enforces its own auth/role/tenant-scope check — never rely on sidebar visibility alone (see Navigation Security Report).

## Anti-patterns confirmed NOT present (safe to rely on)
- No hardcoded category menus baked into individual page components — the vertical catalog section is generated from one shared `VerticalCatalogSection`.
- No second, conflicting mobile nav source — there is currently no mobile nav at all (see Responsive Navigation Report), so there's nothing to keep in sync yet, but if you build one, it must read from the same `NAV_GROUPS`/`TENANT_NAV_GROUPS` arrays, not a duplicate list.
- No runtime mock configuration in the navigation data path.
