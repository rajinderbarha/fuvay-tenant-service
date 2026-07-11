# FINAL-L5-04B — Entitlement Developer Guide

## How to add a module entitlement
Call `entitlement_service.assign_module_entitlement(db, tenant_id=..., module_key=<verticals.key>, actor_id=..., actor_role=...)`. Idempotent — safe to call even if already ACTIVE. Never construct a `TenantModuleEntitlement` row directly; always go through the service (it enforces the idempotent-check, writes the audit row, and increments `version`).

## How to add a category entitlement
Call `entitlement_service.assign_category_entitlement(db, tenant_id=..., category_id=<service_groups.id>, actor_id=..., actor_role=...)`. Requires the tenant to already have an ACTIVE module entitlement for that category's parent vertical — raises `EntitlementConflictError` (map to 409) otherwise.

## How Admin assigns entitlements
Via `/v1/admin/tenants/{tenant_id}/entitlements/{modules|categories}` (`require_super_admin`), or the "Modules & Categories" tab on the Tenant Detail page in super-admin. After any mutation, call `useAdminMenuRefresh()` (super-admin frontend) to refresh the sidebar's vertical-catalog cache — same pattern as FINAL-L5-04's vertical live-refresh fix.

## How Tenant navigation consumes entitlements
`TenantLayout.tsx`'s `EntitlementCtx` fetches `entitlementApi.getMyModules()` on mount, exposes `hasAnyModule` (module-level only — no category-level nav items exist yet). `visibleNavGroups` filters `NAV_GROUPS` to `ALWAYS_VISIBLE_GROUPS` (Overview, More) when `!hasAnyModule`. To add a category-scoped nav item in the future, you'd need to (a) tag the `NavItem` with a `requiresCategory` field, (b) fetch `entitlementApi.getMyCategories()` too, (c) filter at the item level, not just the group level.

## How direct-route guards work
Pattern (see `TenantCatalogService.enable_service()`): resolve the resource's `service_group_id`, call `await entitlement_service.has_category_entitlement(db, tenant_id, service_group_id)`, raise `ServiceOSException("CATEGORY_NOT_ENTITLED", ..., status_code=403)` if false. This must run server-side in the mutation's own service method — never rely on the frontend hiding a button as the actual guard.

## How matching consumes entitlements
**It doesn't yet** — see `FINAL_L5_04B_MATCHING_ENTITLEMENT_REPORT.md`. This is real, unimplemented follow-up work.

## How Staff scope consumes entitlements
**It doesn't yet** — see `FINAL_L5_04B_STAFF_ENTITLEMENT_SCOPE_REPORT.md`.

## How disable/re-enable works
`disable_module_entitlement`/`disable_category_entitlement` set `status='INACTIVE'` (never delete), write an audit row, and (for modules) write a `CASCADED_INEFFECTIVE` audit event for each ACTIVE child category without mutating the child's own status. `reenable_*` sets `status='ACTIVE'` again. Re-enabling a category whose parent module is not ACTIVE raises `EntitlementConflictError`.

## How historical access works
Entitlement checks only guard the **create/enable** path of a resource (e.g., `enable_service`). Read paths (`list_enabled_services`, etc.) are untouched — a tenant's previously-configured, now-un-entitled resources remain fully visible and readable, they just can't be newly created/re-enabled without re-entitlement.

## How cache invalidation works
No query-cache library exists in this codebase. "Invalidation" = explicit `refetch()`/`loadEntitlements()` calls after known mutation points. There is no live cross-tab push — an already-open tenant portal tab will not see an entitlement change until it remounts (reload/navigate).

## How to test tenant isolation
Pattern used throughout this sprint: two fully independent Playwright `browser.newContext()` instances (not the same page with `localStorage.clear()` — that was found to cause flaky `ERR_ABORTED` navigation errors), each logging in as a different tenant, each calling `fetch('/v1/tenant/me/entitlements')` directly and asserting the response never contains the other tenant's category/module.
