# CUSTOMER-L5-03 — Cache Policy

| Query | Scope | Stale time | GC time | Logout | Account switch | Locale | Location | Tenant | Offline |
|---|---|---|---|---|---|---|---|---|---|
| `home.categories(locale, tenantId)` | Public catalogue data (not customer-personalized) | 5 min | 5 min (TanStack default, CUSTOMER-L5-00) | Cleared via `queryClient.clear()` (CUSTOMER-L5-02) — technically unnecessary since this data isn't customer-specific, but clearing everything on logout is simpler and safer than maintaining a "which queries are actually sensitive" allowlist | Same — cleared, then refetched fresh for the new customer | Included in the query key — a locale change produces a cache miss and refetch, never mixed-language stale content | Not a dimension — this backend's categories endpoint has no location/region parameter | Included in the query key (`getRequestTenantId()`) — currently always `"no-tenant"` in this single-tenant test environment, but the key shape is ready for a real value | No disk persistence — in-memory TanStack Query cache only; killing the app clears it (unchanged from the first L5-03 pass's documented decision in `home-cache-and-refresh-policy.md`) |

## Why `queryClient.clear()` on Logout Is Sufficient (Not Excessive)

CUSTOMER-L5-03 §35 says "Do not use one cache policy for every module" —
this is about *stale-time*/*scope* tuning per query, which the table above
does (categories get a 5-minute stale time appropriate for public,
slow-changing catalogue data; a future personalized module would need a
shorter one). It is not an instruction against a single, simple
clear-everything-on-logout policy — CUSTOMER-L5-02's `queryClient.clear()`
already satisfies "personalized content must not persist across
customers" (§35) for every current and future query without needing a
per-query "is this sensitive" flag that could be gotten wrong. This is a
deliberate simplicity tradeoff, not an oversight.

## Home Revision / ETag

**Not applicable** — `GET /v1/customer/categories` has no revision, ETag,
or `generatedAt` field in its real response (see contract matrix). There is
no conditional-fetch/304 support to implement for this endpoint (unlike
CUSTOMER-L5-01's remote-config, which does have ETag support).

## Location Change Invalidation

**Prepared, not exercised** — the query key has no location dimension
because the backend endpoint has no location parameter (see table above).
If a future backend adds region-aware categories, the key shape
(`["home", "categories", locale, tenantId]`) would extend to include a
region segment following the exact same pattern already used for
locale/tenant.
