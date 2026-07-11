# FINAL-L5-04 — Module Visibility Engine Report

## Real, existing engine: `VerticalCatalogService.get_effective_menu()` (backend, `app/engines/vertical_catalog/service.py`)
Live-queried (no caching layer, confirmed by reading the implementation) on every call. For each vertical, returns `is_enabled`, `is_beta`, and its enabled modules (joined from `vertical_catalog_modules` × `catalog_module_definitions`). Also computes `operation_visibility` flags (e.g. `jobs_field_ops`, `security_deposit`, `usage_credits`) by checking whether any *enabled* vertical requires that cross-cutting nav concept — this is a real, working, module-visibility-by-policy engine, not a stub.

## Module examples in this system (real, from live data)
7 verticals exist: `home_services` (enabled), `coaching` (enabled), `real_estate` (enabled), `beauty` (disabled), `restaurant` (beta, disabled), `product_marketplace` (beta, disabled), `professional_services` (beta, disabled). Each carries its own module list (e.g. Home Services' modules include `categories`, `service_groups`, `master_services`, `pricing_rules`, etc., filtered to `is_enabled` per-module before being returned).

## Mapped against the mission's expected states
| Mission state | Real implementation |
|---|---|
| ACTIVE | `is_enabled: true` — appears in sidebar (verified live this sprint) |
| INACTIVE | `is_enabled: false` — disappears from sidebar (verified live this sprint) |
| COMING_SOON | `is_beta: true` — currently rendered as a "Beta" badge, not a distinct "coming soon" visibility state; a beta+disabled vertical (e.g. `restaurant`) still fully disappears from the sidebar like any other disabled vertical, it's simply flagged in the admin UI. No explicit product policy document exists distinguishing "beta" from "coming soon" — flagged as a real terminology/policy gap, not fixed this sprint (a product decision, not an engineering one) |
| HIDDEN | Not a distinct state in the real schema — `is_enabled: false` is the only "not visible" state; `HIDDEN` as a mission-defined 5th state doesn't exist in the implementation |
| TENANT_RESTRICTED | Not implemented — the vertical system is platform-global (an admin concept: "is this vertical available on the platform at all"), not tenant-specific. Tenant-level restriction would be a separate layer (which tenant.vertical a given tenant is assigned) — see Tenant Entitlement Navigation Report for why that layer is currently broken (tenant.category_id always null) |

## Required behavior — verified this sprint
1. **ACTIVE module appears where permitted** — verified live (home_services/coaching/real_estate sections render in the sidebar).
2. **INACTIVE module disappears** — verified live (beauty/restaurant/product_marketplace/professional_services sections absent).
3. **HIDDEN module disappears** — N/A, no distinct HIDDEN state exists; covered by #2's mechanism.
4. **COMING_SOON follows explicit product policy** — no explicit policy exists; `is_beta` is a visual badge only, not a visibility gate.
5. **Tenant-restricted module appears only to eligible tenant** — **not implemented** (real gap, see Tenant Entitlement Navigation Report).
6. **Direct route access to inactive module is blocked or redirected safely** — **not blocked**: `/admin/catalog/beauty` (a disabled vertical) is directly reachable and renders its own detail/config page (with a "Disabled" badge), rather than returning a 403/404. This is a deliberate, defensible design for an **admin configuration tool** (an admin must be able to view/configure a vertical's modules *before* enabling it — blocking access would create a chicken-and-egg problem), not a security gap: the page only exposes catalog *configuration* metadata to an already-authenticated super-admin, the same data class they can see via the Verticals list page itself. Documented explicitly here rather than silently treated as compliant with the mission's literal wording, since the literal wording ("blocked or redirected") is not met, even though the substantive intent (no unauthorized user sees protected content) is.
7. **Historical records remain accessible where policy requires** — not independently tested this sprint (no historical-record-dependent-on-module-status scenario was exercised).

## Result
The module visibility engine is real and provably working for its core case (enable/disable a vertical → sidebar updates live). `TENANT_RESTRICTED` is a genuine, unimplemented gap — see `NOT_READY_FINAL_L5_04_MODULE_VISIBILITY_FAILED` consideration in the Final Report's recommendation reasoning.
