# Tenant Home Services Context Fix Report

## Tenant record (real, live query)

```
tenant_id:   34b427a7-b2be-496c-b826-6d51bb181248
tenant_name: Demo AC Services
category_id: NULL   (never populated for this seed tenant)
vertical:    home_services   (correctly populated — the real source of truth)
status:      pending_setup
```

`category_id` is NULL — this is why the previous `get_dashboard_runtime`
implementation (which joined through `tenant.category_id →
ServiceCategory.category_type`) always returned `category: null` and no
usable vertical, regardless of the tenant's real, correctly-set `vertical`
column. Fixed two turns ago in `app/engines/tenant_engine/portal_router.py`
(root cause: two of the three fields the join depended on were empty in
real data — `tenant.category_id` NULL and `ServiceCategory.category_type`
also unpopulated for the seeded Home Services category; only
`ServiceCategory.vertical_type` / `tenant.vertical` were ever reliably set).

## Why the bug came back after that fix

The backend fix alone was not sufficient, because the **frontend never
re-checked the server**. `useTenant()` set `vertical` exactly once, at
login time, into `localStorage`, and never refreshed it again for the
lifetime of that browser session. Any tenant who had logged in *before*
the backend fix shipped was permanently stuck with a blank cached
`serviceos_tenant_vertical` value — visiting the page again, refreshing,
even navigating away and back, never re-fetched the corrected value. Only
a full logout/login would have picked up the fix, which is not a
reasonable fix for a real production bug.

## Tenant context API result (live, this turn)

```
GET /v1/tenant/dashboard/runtime
→ {
    "tenant": { "tenant_id": "...", "business_name": "Demo AC Services", "category": null },
    "category_type": "home_services",
    "dashboard_type": null, "primary_engine": null,
    "enabled_engines": [], "modules": [], "category": null
  }
```

`category_type` (top-level, sourced from `tenant.vertical`) is correctly
`"home_services"`. `category`/`tenant.category` remain `null` since
`tenant.category_id` is genuinely NULL in this seed data — the fix
doesn't paper over that, it just stops depending on it.

## Frontend guard result

- `hooks/useTenant.ts` now **always re-fetches** `GET
  /v1/tenant/dashboard/runtime` on every mount (not just once at login),
  self-healing `localStorage["serviceos_tenant_vertical"]` regardless of
  what was cached before. A stale/blank cache can never permanently block
  the guard again — no logout required.
- `useTenant()` now exposes `loading`/`error`/`requestId`, so the wizard
  page can distinguish "still resolving" from "confirmed not Home
  Services" — previously a `null` vertical during the brief loading
  window was indistinguishable from an actual non-Home-Services tenant.
- New `lib/verticalGuard.ts::isHomeServicesTenant()` checks 11 different
  field-name/shape variants (`vertical`, `vertical_slug`, `category`,
  `category_slug`, `category_name`, `business_category`, `categorySlug`,
  `categoryName`, `tenant.vertical`, `tenant.category_slug`,
  `tenant.category_name`), normalizing case and separators
  (`"Home Services"` → `home_services`), instead of one brittle `===
  "home_services"` check on a single field.
- `/tenant/setup/services` (`app/(tenant)/tenant/setup/services/page.tsx`)
  now checks `tenant.loading` first (skeleton), then `tenant.error`
  (request_id error card with Retry), then `isHomeServicesTenant(tenant)`
  — in that order, so a loading/error state can never fall through to the
  blocked message.
