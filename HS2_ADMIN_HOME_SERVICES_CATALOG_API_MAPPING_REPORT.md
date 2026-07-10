# HS2 — API Mapping Report

## Real endpoints used by the catalog console (unchanged this sprint, verified via source)
| Ticket-suggested | Real endpoint |
|---|---|
| `GET /v1/admin/home-services/catalog` | `homeServicesCatalogConsoleApi.listServices()` — real backend call in `home_services_catalog_console_router.py` |
| `GET /v1/admin/home-services/catalog/summary` | Not a dedicated endpoint — this sprint's new health cards are computed **client-side** from the already-fetched `listServices()` payload, not a new summary call |
| `GET /v1/admin/home-services/catalog/services/{service_id}` | `homeServicesCatalogConsoleApi.getServiceDetail(id)` — real |
| Types/brands endpoints | Real, but this sprint removed the pricing-mutation calls (`setTypeLimits`, `setBrandLimits`, `setBrandBehavior`, `pricePreview`) from this page entirely — those endpoints still exist in `lib/api.ts` and the backend, just no longer called from the catalog console (by design, per HS2 scope) |
| Issues | `masterDataApi.listIssueTypes({ master_service_id })` — real |
| Options | `masterDataApi.listServiceOptions({ master_service_id })` — real |
| Activity | `homeServicesCatalogConsoleApi.getAudit(serviceId)` — real |

## Not real / not built
- No `POST/PUT` group endpoints exist or are called (no group CRUD UI —
  see CRUD Report).
- No dedicated `catalog/summary` endpoint — health cards derive from the
  list payload's per-service fields (`is_active`, `is_type_required`,
  `types_count`, `is_brand_required`, `brands_count`,
  `requires_issue_type`, `tenant_override_allowed`), all real fields
  already present on `HsConsoleService`.

## No mock data
Confirmed: every value rendered on the page (including the new health
cards) traces back to a real API response. No hardcoded arrays, no fake
service lists.

## Verdict
API integration: **real, no mock data**, but narrower than the ticket's
suggested endpoint list — group management and a dedicated summary
endpoint don't exist and weren't added this sprint.
