# CUSTOMER-L5-03 — Security Review

Static/code-level review — no live backend to fuzz-test against (same
constraint as CUSTOMER-L5-02, see `CUSTOMER-L5-03-runtime-evidence.md`).

## Runtime Validation

Every category item from `GET /v1/customer/categories` is Zod-validated
(`category-schema.ts`) before it can render — malformed items are dropped,
not rendered as-is. Icon/banner URLs are constrained to `https://` or a
relative path (rejects `javascript:`, `data:`, arbitrary schemes) — see
`CategoryCard.tsx#isTrustedImageUrl`, unchanged from the first pass.

## Unsafe Route Rejection

Category press does not navigate anywhere (no destination exists) — there
is no route string from the backend that could be misused, because no
backend field is ever treated as a route. `resolveModuleRenderer` (this
pass) never executes a component name string from any source; it only
compares against a compiled allowlist (`SUPPORTED_MODULE_TYPES`).

## Tenant / Marketplace Isolation

**UNVERIFIED** — this environment has one marketplace and no multi-tenant
test fixtures reachable. `home-queries.ts`'s query key includes
`getRequestTenantId()` (real, newly wired this pass) so *if* a tenant
context were ever set, cache isolation would follow automatically — but
this was not exercised end-to-end. Documented honestly as UNVERIFIED, not
claimed as tested.

## Cross-Customer Cache Isolation

Categories are not customer-personalized, so there is no per-customer
leakage risk for this specific query. `queryClient.clear()` on logout
(CUSTOMER-L5-02) still wipes it regardless, as a blanket policy — see
`CUSTOMER-L5-03-cache-policy.md`.

## Sensitive Analytics / Logging

No analytics wired (no vendor). Logging (`home_module_skipped`,
`home_module_validation_failed`) never includes category names/IDs/images
— only counts and the (compiled, non-sensitive) module type string.

## Production Mock Scan

Grep confirms no hardcoded category list, no hardcoded service data, no
fake recommendation/popularity/price anywhere in `features/home/`. The one
module (`category-grid`) is entirely backend-driven; its visibility/order
comes from `evaluateModuleVisibility`/`composeCategorySections`, not a
static array.
