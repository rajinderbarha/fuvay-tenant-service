# FINAL-L5-04 — Input Artifact Review

## Honest correction: two referenced input reports do not exist
`docs/final-l5-00b/` does not exist at all in this repository. `FINAL_L5_00B_DUPLICATE_ROUTE_DECISION_REPORT.md` and `FINAL_L5_00B_DISCONNECTED_PAGE_CLASSIFICATION_REPORT.md` were never created in any prior sprint — confirmed via direct directory listing, not assumed. This mirrors a pattern seen in earlier FINAL-L5-* sprints (e.g. "Staff/Technician frontend" turning out to be routes within tenant-portal, not a separate app): the mission text references planned artifacts that were never actually produced. This sprint proceeds using the real reports that do exist (`FINAL_L5_00_ROUTE_PAGE_INVENTORY.md`, `FINAL_L5_00_MENU_NAVIGATION_INVENTORY.md`) rather than fabricating the missing decision reports.

## Reconciling the mission's cited figures against the real FINAL-L5-00 report
| Mission's figure | Real FINAL-L5-00 data | Reconciliation |
|---|---|---|
| "281 routes inventoried" | 144 (super-admin) + ~95 tenant-portal + 11 staff-web + 8 (customer) + 8 (mobile staff) ≈ 266 | Close but not exact — plausibly a different counting method (e.g. including redirect stubs differently); not force-fit to 281 |
| "79 disconnected pages" | ~35 top-level orphans + ~35 orphaned detail pages (super-admin) + 9 (tenant-portal) ≈ 79 | **Matches closely** when both top-level and detail-page orphans are counted together |
| "37 duplicate route entries" | 10 clusters / ~22 routes (super-admin) + 11 clusters / ~30 routes (tenant-portal) ≈ 21 clusters, ~52 routes | **Does not cleanly match** either the cluster count (21) or route count (52) — reported honestly as a discrepancy, not silently reconciled |
| "0 broken route targets" | Confirmed — FINAL-L5-00's own classification taxonomy includes `BROKEN_ROUTE` and it was used zero times across all 4 applications | **Matches exactly** |

## Real findings from FINAL-L5-03 re-confirmed relevant this sprint
- `lib/nav-config.ts` (tenant-portal) is 100% static/hardcoded — `TENANT_NAV_GROUPS` contains no `moduleKey`/`categoryId`/`tenantEntitlementKey` fields and is rendered unconditionally.
- `usePermissions()` exists in super-admin (3 consumers, under-adopted) — FINAL-L5-03 initially missed this, then corrected it.
- No query-cache library exists in any of the 3 apps (`useApi`/`useAction` hand-rolled hooks).

## New, significant finding this sprint (not previously documented)
A **real, working, backend-driven dynamic vertical/module menu system already exists** in super-admin: `verticalCatalogApi.getEffectiveMenu()` (`GET /v1/admin/verticals/navigation/effective-menu`) returns live, DB-queried (no caching) per-vertical enabled-module data, rendered by `AdminLayout.tsx`'s `VerticalCatalogSection` as expandable sidebar sections after the "Catalog" group. This is real, substantial prior infrastructure this sprint builds on rather than reinvents — see Route/Navigation Registry and Category Menu Generation reports for full detail.

## New, significant gap found this sprint
`tenant.category_id` is **NULL for every seeded tenant** (confirmed via direct DB query), even though `tenant.vertical` is correctly populated (`'home_services'`). The tenant-portal backend's `enabled_engines`/`modules` resolution (`app/engines/tenant_engine/portal_router.py::get_dashboard_runtime`) depends on `tenant.category_id`, which is always empty in practice — so this data source, if wired into a dynamic tenant sidebar, would return empty and hide everything. A prior sprint (test file `test_tenant_home_services_vertical_detection_fix.py`) already fixed an analogous issue for `category_type` by falling back to `tenant.vertical`, but that fallback was never extended to `enabled_engines`/`modules`. This is the central blocker discussed throughout this sprint's reports — see Tenant Entitlement Navigation Report.

## Result
Input review complete, with real discrepancies and gaps documented honestly rather than glossed over.
