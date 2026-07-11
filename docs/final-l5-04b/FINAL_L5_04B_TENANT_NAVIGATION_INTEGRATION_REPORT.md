# FINAL-L5-04B — Tenant Navigation Integration Report

## Real mechanism: `EntitlementCtx` in `TenantLayout.tsx`
On shell mount, `entitlementApi.getMyModules()` is called (real live API, no mock), populating `entitledModuleKeys`. A `refresh()` function is exposed via context for future call sites that mutate entitlement from within the tenant portal itself (none exist yet — all mutation happens admin-side).

## Real, browser-verified gating: module-level, not category-level
`visibleNavGroups = hasAnyModule ? NAV_GROUPS : NAV_GROUPS.filter(g => ALWAYS_VISIBLE_GROUPS.has(g.label))` — when the tenant has **zero** active module entitlements, only "Overview" (Dashboard) and "More" (Documents/Notifications/Activity/Settings) groups remain; Setup/Team/Operations/Finance/Engagement/Insights all disappear.

**Real Chromium E2E evidence** (`final-l5-04b-entitlement.spec.ts`): disabled Tenant One's only module entitlement via the admin UI, opened a fresh tenant-portal session, and the sidebar `<nav>` element's own text content was captured directly (not just body-text scraping, which was found to give false results due to CSS `text-transform:uppercase` altering rendered text case) — confirmed `Bookings` and `Security Deposit` (Operations/Finance group items) were absent, `Dashboard` remained. Re-enabled, and a fresh live API call confirmed `home_services` reappeared in `/v1/tenant/me/modules`.

## Honest gap: no category-level tenant nav gating
Investigated directly: the tenant-portal's static `NAV_GROUPS` (in `TenantLayout.tsx`) has **no category-specific items** — items like "Services", "Pricing", "Service Setup" are generic/module-level, not tied to a specific category (e.g., there's no "AC Services" menu item to hide when AC entitlement is disabled). This is a genuine, pre-existing architectural characteristic of the tenant portal (confirmed via source read of `nav-config.ts` and `TenantLayout.tsx`'s local `NAV_GROUPS`), not something this sprint should fabricate a fix for by inventing new menu items with no corresponding pages. **Category-level entitlement is real and enforced at the data/backend layer** (proven via Service Setup Enforcement's 403 guard) even though no category-specific sidebar item exists to visually hide.

## Required checks
| # | Check | Result |
|---|---|---|
| 1 | Tenant One sees only entitled modules/categories | Module-level: yes, verified live. Category-level: no visual nav distinction exists to check (see gap above) — but backend enforcement is real (proven elsewhere) |
| 2 | Tenant Two sees its own different set | Verified via real API (`plumbing` not `ac_services`) — same honest module/category distinction applies |
| 3 | Disabled entitlement disappears | **Verified live** for module-level nav |
| 4 | Re-enabled entitlement returns | **Verified live** |
| 5 | Read-only users retain permitted read routes | Not independently re-tested this sprint (unrelated to entitlement changes; established in earlier sprints, unaffected) |
| 6 | Mutation routes remain blocked | Backend-enforced regardless of nav visibility (see Direct Route Guard Report) |
| 7 | No hardcoded tenant category list | Confirmed — `ALWAYS_VISIBLE_GROUPS` is a set of *group labels* (a UX constant, not a category name), and the actual gating value (`entitledModuleKeys`) comes entirely from the live API, never a hardcoded array of category names |
| 8 | Desktop and mobile use the same entitlement result | Both read the same `EntitlementCtx` — there is only one nav source (no separate mobile config to diverge, consistent with FINAL-L5-04's finding that no distinct mobile nav exists yet) |

## Result
Real, live, browser-proven module-level gating. Category-level gating is real at the backend/data layer but has no UI surface to hide in the tenant portal's current architecture — documented as an honest gap, not silently claimed complete.
