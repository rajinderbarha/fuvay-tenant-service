# CUSTOMER-L5-03 — Home Architecture (Deepened Pass)

Supplements `home-architecture.md` (first pass, still accurate for the
screen-level data flow) with the module-registry layer added this pass.

## Data Flow (Updated)

```
HomeScreen
  ├─ resolveModuleRenderer("category-grid")     [domain/module-registry.ts]
  │    → { recognized: true, moduleType: "category-grid" }
  ├─ evaluateModuleVisibility(module, context)   [domain/module-visibility.ts]
  │    → "VISIBLE" | "AUTH_REQUIRED" | "UNSUPPORTED_VERSION" | ...
  │    → critical + non-VISIBLE → page-level ErrorState (logged once via useEffect)
  └─ useHomeCategories()                         [queries/home-queries.ts]
       → homeQueryKeys.categories(getRequestLocale(), getRequestTenantId())
       → homeApi.listCategories()  → GET /v1/customer/categories
       → parseCategoryList()       → Zod validation, drops invalid items
       → composeCategorySections() → dedupe, stable sort, cap at 12
```

## API Ownership vs. Remote-Config Ownership

Unchanged from CUSTOMER-L5-01's general rule (`remote-configuration.md`):
remote config would determine whether a module *family* is allowed at all;
the Home API determines actual instances/content. In practice this sprint,
remote config plays no role in Home at all — there is no `home`-related
field in the remote-config schema (CUSTOMER-L5-01's schema has no module
list matching this backend's real categories), so the one real module
(`category-grid`) is unconditionally attempted, gated only by the
module-visibility evaluator's `AUTH_REQUIRED`/`UNSUPPORTED_VERSION` checks.

## Module Registry

See `CUSTOMER-L5-03-module-registry.md`.

## Query Keys

See `CUSTOMER-L5-03-cache-policy.md`. Fixed this pass: `getRequestLocale()`
is now a real, live value (see baseline-verification's locale-header
defect writeup) instead of a hardcoded `"en"` string.

## Tenant Isolation

`getRequestTenantId()` is wired into the query key but never set to a real
non-`undefined` value anywhere in this codebase — there is no
multi-tenant-selection flow yet. The architecture is ready; the isolation
itself is UNVERIFIED (see security review).

## Error Isolation

Unchanged principle from the first pass (module failure doesn't blank the
whole page) — now formalized through `criticalModuleUnavailable` rather
than being implicit in "the only section on the page happens to have its
own ErrorState."

## Offline Behavior

Unchanged from `home-cache-and-refresh-policy.md` (first pass) — no disk
cache, `OfflineBanner` shown independently of the Services section's own
error/empty state.

## Analytics

Not wired (no vendor) — unchanged.
