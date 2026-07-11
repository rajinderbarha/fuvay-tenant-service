# FINAL-L5-04B — Entitlement Domain Service Report

## Real, single canonical service: `app/engines/entitlement/service.py::EntitlementService`
Both the Admin router and the Tenant self-read router, plus the Service Setup enforcement guard, all call **the same service instance** (`entitlement_service`, a module-level singleton) — no duplicated entitlement logic exists anywhere else in the codebase (verified by grep: `tenant_module_entitlements`/`tenant_category_entitlements` are only ever queried from within `service.py`).

## Implemented operations (mission's suggested list, all present)
| Operation | Implemented | Notes |
|---|---|---|
| `get_tenant_modules(tenant_id)` | Yes | `effective_only` param controls whether disabled rows are included |
| `get_tenant_categories(tenant_id, module_id?)` | Yes | optional module filter |
| `has_module_entitlement(tenant_id, module_key)` | Yes | used nowhere yet outside tests — reserved for future guard points |
| `has_category_entitlement(tenant_id, category_id)` | Yes | **actively used** — real backend guard on `TenantCatalogService.enable_service()` |
| `assign_module_entitlement(...)` | Yes | idempotent — re-assigning an ACTIVE row returns it unchanged, no duplicate INSERT |
| `disable_module_entitlement(...)` | Yes | implements `CASCADE_STATUS_UPDATE`-adjacent policy (see Module Disable Cascade Policy) |
| `assign_category_entitlement(...)` | Yes | validates parent module entitlement first, 409 if missing |
| `disable_category_entitlement(...)` | Yes | |
| `resolve_effective_entitlements(...)` | Yes | now takes `effective_only` flag — **fixed this sprint** after a real bug was found where the Admin UI couldn't see (and therefore couldn't re-enable) disabled rows because this method always filtered to effective-only |

## Centralization requirements — all met
1. No entitlement logic duplicated across routers — confirmed by grep, single call site pattern.
2. Effective-date logic centralized in one private `_is_effective()` helper, used by every read path.
3. Status logic centralized — no router or other module reads/writes `.status` directly.
4. Module/category parent validation centralized in `assign_category_entitlement` (resolves `service_group.category_id` → `service_category.vertical_type` → `verticals.key` → active module entitlement check, in one place).
5. Tenant isolation enforced centrally — every method takes an explicit `tenant_id` and every SQL `WHERE` clause filters on it; no method accepts a caller-supplied "trust me" tenant scope.
6. Historical-access policy explicit — soft-disable only (`status='INACTIVE'`), never a `DELETE`, documented in the Historical Access Policy report.

## Real bug found and fixed via this sprint's own dogfooding
`disable_module_entitlement`'s cascade-audit step originally tried to write `"ACTIVE (parent module inactive)"` (32 characters) into `entitlement_audit_log.new_status`, a `VARCHAR(20)` column — a real `500 StringDataRightTruncationError`, caught via live curl testing during E2E prep, not caught by the mocked-DB unit tests (mocking hides real column-length constraints). Fixed to write a valid, ≤20-char status and move the explanation into the `reason` text field. A regression test (`TestCascadeAuditColumnLengths`) was added that statically scans the service module's source for any hardcoded `new_status`/`previous_status` string literal exceeding 20 characters, to prevent recurrence.

## Result
One real, centralized service; all suggested operations implemented; one real production bug found and fixed during this sprint's own testing, with a regression test added.
