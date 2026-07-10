# Sidebar Active-State Fix Report (Part 3)

## Root cause
`AdminLayout.tsx` highlights a sidebar item via exact string equality: `active={activeNav === item.id}`.
The `activeNav` value was computed in `app/admin/layout.tsx` by calling
`resolveAdminNavId(pathname)` from `lib/nav-config.ts`, which mapped only the FIRST path segment
after `/admin` to a nav id via a hand-maintained `ADMIN_PATH_TO_NAV_ID` record (plus one special
case for `home-services`). Any route with a second-level segment that has its OWN sidebar entry
(e.g. `/admin/users/roles` → "Roles", `/admin/users/permissions` → "Permissions",
`/admin/tenants/onboarding` → "New Requests", `/admin/onboarding/providers` → "Verify & Approve")
always resolved to the PARENT segment's id (`users`, `tenants`, `onboarding`) instead of its own,
so the wrong sidebar item lit up (or, for `/admin/onboarding/providers`, an id ("onboarding") that
didn't even match any real item, since the real item's id is "onboarding-providers").

## Fix
- `components/layout/AdminLayout.tsx`: added `FLAT_NAV_HREFS` (flattened `{id, href}` from the
  real, rendered `NAV_GROUPS` — single source of truth for what's actually in the sidebar) and
  `resolveActiveNavId(pathname)`, which picks the nav item whose `href` is the **longest matching
  prefix** of the current pathname (segment-boundary safe: `/admin/catalog` does not match
  `/admin/catalog-module`). Both exported.
- `app/admin/layout.tsx`: now calls `resolveActiveNavId` instead of the old
  `lib/nav-config.ts`-backed `resolveAdminNavId`.
- Parent nav groups: groups aren't collapsible/expand-tracked in this sidebar design (all groups
  render fully open at all times — no expand/collapse per group, only the per-vertical Catalog
  sub-sections expand/collapse, and those already compute `isActiveSection` from `activeNav`
  matching one of their own module ids, so they inherit the same, now-correct, prefix-matched id).

## Browser verification (Playwright, real browser, `frontend/e2e-admin-tenant/e2e/admin-shell-e2e02.spec.ts`)
6 nested routes tested, each checked for `getComputedStyle(#nav-<id>).fontWeight === 600` (the
active-item style): all 6 **PASS**.
```
/admin/home-services/pricing-rules   -> nav-hs-pricing-rules      fontWeight=600
/admin/home-services/service-catalog -> nav-hs-service-catalog    fontWeight=600
/admin/tenants/onboarding             -> nav-onboarding            fontWeight=600
/admin/onboarding/providers           -> nav-onboarding-providers  fontWeight=600
/admin/users/roles                    -> nav-roles                 fontWeight=600
/admin/users/permissions              -> nav-permissions           fontWeight=600
```
Screenshots saved at `frontend/e2e-admin-tenant/evidence/e2e02/_admin_*.png`. Log:
`frontend/e2e-admin-tenant/evidence/e2e02/active-state.log`.

Before the fix, `/admin/users/roles` and `/admin/users/permissions` both would have highlighted
"Users" instead of "Roles"/"Permissions" (verified by re-reading old `nav-config.ts` logic; not
re-run against pre-fix code since the fix is a small, low-risk, already-verified change).
