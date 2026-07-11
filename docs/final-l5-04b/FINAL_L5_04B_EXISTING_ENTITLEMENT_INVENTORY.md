# FINAL-L5-04B — Existing Entitlement Inventory

Real investigation of the codebase before any new code was written (delegated to a dedicated read-only exploration pass, cross-verified with direct source reads and live DB queries).

## `tenants` (`app/engines/tenant_engine/models.py`, class `Tenant`)
| Column | Purpose | Status |
|---|---|---|
| `vertical` (String(50), NOT NULL) | Real, always-populated source of truth (e.g. `home_services`) | Canonical today |
| `category_id` (UUID, nullable, no FK constraint) | "Sprint 4: category_id from admin_catalog" | **Always NULL in practice** — confirmed live: both real tenants (`demo-ac-services`, `isolation-test-services`) have `category_id = NULL` |
| `plan_type` (String(30)) | Loose plan concept | No category/module linkage |
| `TenantFeatureFlag` (separate table) | Generic `tenant_id` + `flag_key` + `flag_value` (JSONB) k/v store | Arbitrary-key, not module/category-typed — closest existing "capability flag" concept, but not fit for purpose |

**Conclusion: `tenant.category_id` is unused/dead in practice** — every real code path (portal_router, canonical seed) already routes around it via `tenant.vertical` or `master_services`/`tenant_services` lookups.

## Module concept (`app/engines/vertical_catalog/models.py`, migration 089)
| Table | Purpose | Scope |
|---|---|---|
| `verticals` | Platform verticals (home_services, coaching, real_estate…) | **Global** toggle, not tenant-scoped |
| `catalog_module_definitions` | Master list of admin sidebar modules | Global |
| `vertical_catalog_modules` | M2M vertical↔module, which modules are enabled per vertical | Global |
| `vertical_menu_config` | Per-vertical sidebar menu ordering | Global |

`VerticalCatalogService.get_effective_menu()` takes **no `tenant_id` parameter** — purely global/admin-level, confirmed by direct source read.

## Category concept (`app/engines/admin_catalog/models.py`)
| Table | Purpose |
|---|---|
| `service_categories` | 14 top-level categories (Home Services, Salon, Coaching…), has `vertical_type`/`category_type` string fields that loosely echo `Tenant.vertical`, **no FK to `verticals`** |
| `service_groups` | Intermediate grouping under a category (e.g. "AC Services", "Plumbing" under "Home Services") — **this is the real granularity the mission's "AC Services category" example refers to**, confirmed via live seed data (`ac_services`/`plumbing` are `service_groups` rows, not `service_categories` rows) |

## Existing tenant-module / tenant-category join tables
**None found.** Grep for `tenant_module|tenant_categor|tenant_capabilit|tenant_feature|tenant_offering|tenant_enablement` across the repo found no dedicated M2M entitlement table. The closest existing pattern is `tenant_services` (tenant ↔ `master_service_id`, service-level not category/module-level, unique `(tenant_id, master_service_id)`) — this establishes the repo's own convention (base UUID PK, `tenant_id` + target FK, `UniqueConstraint`, status field, indexes) that the new tables mirror.

## Packages/subscriptions imply no real entitlement
`service_packages` (migration 072) has a loose `vertical_type` string field and `package_type`/`plan_level`, but **no `category_id` FK**. A latent bug was found: `category_runtime_router.py` joins `tenant_package_assignments.category_id`, a column that **does not exist** on that table (verified against the ORM model and migration 072) — wrapped in a broad `try/except` that silently falls back to zero counts. This confirms packages today grant **no modeled category-level entitlement at all**.

## Determinations
1. No tenant-module relation exists under another name.
2. No tenant-category relation exists under another name.
3. Packages/plans do **not** imply real entitlement (string-based, unenforced `vertical_type` only).
4. `tenant.category_id` is confirmed unused/legacy in practice (always NULL for real tenants).
5. Category ownership (`service_groups` → `service_categories`) is global, not vertical-specific by FK — only loosely linked via string matching (`ServiceCategory.vertical_type` ≈ `Vertical.key`).

See `existing-entitlement-inventory.json` for the machine-readable version of this table.
