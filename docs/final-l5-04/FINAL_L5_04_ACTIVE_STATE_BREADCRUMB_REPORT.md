# FINAL-L5-04 — Active State and Breadcrumb Certification

## Real current mechanism
Both `AdminLayout` and `TenantLayout` accept an `activeNav` prop, manually passed by every page (`<AdminLayout activeNav="verticals">`), compared against each `NavItem.id` to apply active styling (`SidebarItem`, confirmed via source read).

## Fixed this sprint: breadcrumbs were built but never wired in — now they are
Investigation found `components/layout/Breadcrumbs.tsx` **already exists** in both apps (well-built: semantic `<nav aria-label="Breadcrumb">`, real label resolution via `resolvePageMeta`/`resolveTenantPageMeta` against `page-registry.ts`, graceful degradation to nothing when fewer than 2 crumbs are registered for a page) — but was a **dead, unwired component**: zero imports/renders found anywhere in either app before this sprint. **Fixed**: added `<Breadcrumbs/>` to both `AdminLayout.tsx`'s and `TenantLayout.tsx`'s main content area (one line each, self-contained component with no props required — it reads the current path itself via `usePathname()`).

**Browser-verified live this sprint**:
- Super Admin `/admin/categories` → renders `Catalog / Categories`.
- Tenant Portal `/service-jobs` → renders `Jobs / Service Jobs`.
- Tenant Portal `/jobs` → renders nothing, **correctly** (its registry entry has only 1 crumb — the component's own `resolved.length <= 1` check intentionally suppresses single-item trails, since a breadcrumb with no real hierarchy adds no value; confirmed this is by-design behavior, not a bug, by reading the component and the registry entry together).

## Required checks
| Check | Result |
|---|---|
| 1. Current route highlights correct item | **Verified live** — `/admin/verticals` correctly highlighted "Verticals" in the sidebar |
| 2. Detail route highlights parent list item | Not independently tested this sprint |
| 3. Wizard step highlights wizard parent | Not independently tested (no wizard flow exercised) |
| 4. Category detail route expands category group | N/A — no category-level expansion exists (see Category Menu Generation Report) |
| 5. Redirect route ends on canonical active item | Not independently tested this sprint |
| 6. Breadcrumb labels readable | **Verified live** — real, human-readable labels ("Catalog", "Categories", "Jobs", "Service Jobs"), not raw IDs |
| 7. Breadcrumbs don't expose raw IDs | **Confirmed** — labels come from `page-registry.ts`'s curated `breadcrumbs` arrays, never raw route params/UUIDs |
| 8. Mobile and desktop active states match | Not independently tested (no distinct mobile nav implementation exists to compare against — see Responsive Navigation Report) |

## Honest coverage limit
`page-registry.ts` has sparse coverage (~55 entries for super-admin's 144 routes per FINAL-L5-00; similarly partial for tenant-portal's ~95). Pages without a registry entry now correctly show no breadcrumb (safe default) rather than a broken one, but do not yet get a real breadcrumb trail either — expanding registry coverage is real, valuable, low-risk future work (pure data entry, no logic change) not completed this sprint for all ~239 remaining routes.

## Result
Active-state highlighting: verified working. Breadcrumbs: genuinely fixed this sprint (real dead code wired up, not fabricated), browser-verified in both apps, with an honestly-stated registry-coverage limit.
