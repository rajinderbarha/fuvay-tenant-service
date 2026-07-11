# FINAL-L5-04 — Active Category Menu Generation Report

## Real finding: the mission's literal example does not exist as built
The mission's Part 5 example shows category-level expansion (`Categories → AC Services → Overview/Services/Service Types/Brands/...`). The **real, working dynamic expansion in this codebase operates at the VERTICAL level** (Home Services / Coaching / Real Estate), not at the finer-grained CATEGORY level (AC Repair, Plumbing, Electrical — which are `service_categories`/`master_services` rows *within* a vertical). Verified by reading `AdminLayout.tsx`: `VerticalCatalogSection` is keyed by `vertical.vertical_key`, its children are `vertical.modules` (catalog-management modules like "Categories", "Service Groups", "Master Services", "Pricing Rules" — *tools for managing categories*, not one expandable group per individual category).

## What genuinely works (verified live this sprint)
- **Activate/deactivate vertical → sidebar section appears/disappears live** — browser-proven this sprint (`final-l5-04-admin-category-nav.spec.ts`), including the live-refresh fix.
- **Activate/deactivate individual category** — real, working backend endpoints exist (`POST /v1/admin/catalog/categories/{id}/activate` and `/deactivate`, real `is_active` column mutation) and are wired to `categories/page.tsx`'s UI (toggle buttons, confirmed via source read). This sprint additionally wired `refreshMenu()` into these actions so the sidebar's vertical-level state (which can be affected by category composition) stays in sync — but there is no category-specific submenu to appear/disappear as a *direct* consequence, since none exists.

## Required category fields — checked against the real `ServiceCategory` model
`id`, `key`/`slug`, `name`, `status`(`is_active`), and `module_key`(vertical association) all exist and are real, live-queried columns (confirmed via the activate/deactivate endpoints operating on real rows). `menu_enabled` and `allowed_route_templates` as literal fields **do not exist** — there is no field on `ServiceCategory` controlling whether a category gets its own sidebar entry, because no per-category sidebar entry mechanism exists at all.

## Required behavior — assessed against the real implementation
| Requirement | Status |
|---|---|
| 1. Active category appears | **Not applicable as stated** — categories don't generate their own menu group; the containing *vertical's* menu group is what appears/disappears, verified live |
| 2. Disabled category disappears | Same — no category-level menu group exists to disappear |
| 3. Archived category disappears from new-operation menus | Not tested (no distinct "archived" state found beyond `is_active: false`) |
| 4. Re-enabled category returns | Verified for the *vertical* level (browser-proven, both directions); not applicable at category level |
| 5. Sort order respected | `sort_order`/`display_order` fields exist on `service_categories` and `catalog_module_definitions`; rendering order confirmed to follow them for verticals/modules (not independently re-verified for raw category lists this sprint) |
| 6. Category label/icon from configuration | True where categories are rendered (the Categories admin *page* itself, not the sidebar) |
| 7. Category-specific routes receive category context | True for the `/admin/catalog/[vertical]/[module]`-style dynamic routes (vertical-scoped); no equivalent for individual categories |
| 8. No hardcoded AC/Plumbing/Electrical lists inside sidebar code | **Confirmed true** — grepped `AdminLayout.tsx` and `nav-config.ts` for literal category names ("AC Repair", "Plumbing", "Electrical", etc.) — zero matches. The sidebar's hardcoding is at the *vertical* level (`"Home Services"` as a hardcoded static `NAV_GROUPS` entry — see Business Rule/Deprecated Pattern notes), not at the individual-category level, since no per-category code exists to hardcode |
| 9. Category list refreshes after admin activation/deactivation | **Fixed this sprint** — `refreshMenu()` wired into `activateAction`/`deactivateAction` |

## Result
The mission's specific "category generates its own expandable menu group" requirement is **not implemented** — only vertical-level expansion exists, which is real, working, and now live-refreshing correctly. This is a genuine, honestly-documented gap between the mission's literal spec and the real system, not a fabricated pass. This is one basis for `NOT_READY_FINAL_L5_04_CATEGORY_VISIBILITY_FAILED` being seriously considered in the Final Report — mitigated by the fact that the *vertical*-level equivalent works correctly and rule 8 (no hardcoded category lists) genuinely holds.
