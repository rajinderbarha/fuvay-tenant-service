# Legacy Review Frontend Caller Audit — Slice 2F-25

## Method — all six known applications searched

`frontend/customer-app`, `frontend/super-admin`, `frontend/tenant-portal`,
`frontend/e2e-admin-tenant`, `mobile/customer-app`, `mobile/staff-app`.

Searched for the literal `/v1/reviews` prefix across source and shared API
clients. This exhaustive-first approach is deliberate: Slice 2F-24's caller
audit initially claimed "no callers exist" for the canonical engine and was
wrong, which is exactly how a security fix ships a user-visible break.

## Callers found

| App | File | Endpoints |
|---|---|---|
| **tenant-portal** | `lib/api.ts` (`reviewsApi`, ~924-952) | list `?tenant_id=`, aggregates, reply, flag, resolve, requests list `?tenant_id=`, requests create (tenant_id in body) |
| super-admin | `lib/api.ts` (`reviewApi`, ~2327-2338) | flag, list — **object defined but not imported** by the reviews page, which reads the canonical `/v1/admin/reviews*` stack (confirmed in Phase 1A `review-canonical-decision.md`) |
| customer-app / e2e / mobile ×2 | — | **no legacy callers** |

## Compatibility: no frontend change required

Every tenant-portal call supplies its **own** tenant:

```ts
const tid = getTenantId();
const qs  = new URLSearchParams({ ...params, tenant_id: tid ?? "" });
...
body: JSON.stringify({ job_id, tenant_id: tid, customer_id, staff_id })
```

`_effective_tenant` refuses a **mismatching** client tenant but accepts a
**matching** one, so these calls continue to work unchanged. Rejecting the
field outright would have broken seven live calls for no security gain — the
value is no longer authoritative either way.

Asserted by `test_tenant_portal_sends_its_own_tenant_id`, so the compatibility
basis for that design decision cannot silently disappear.

## Two pre-existing frontend/backend mismatches — reported, NOT fixed

1. **`reply` sends the wrong field.** The client posts
   `{ reply_text }` while the route reads `body["reply"]` — a `KeyError`, i.e.
   HTTP 500. The legacy reply capability has therefore been **broken from the
   UI all along**, independent of this slice.
2. **`resolve` is called by the tenant portal** but the route is
   `require_super_admin`, so a tenant user receives 403.

Neither was corrected. Fixing (1) would *enable* a currently-dead write path
into the superseded `reviews` table, which is the opposite of the intended
direction — the canonical engine is `customer_reviews`. Both are recorded in
`known-limitations.md` as evidence that these legacy capabilities are
dead-in-practice from the UI.

## Deterministic guard added

`TestFrontendCallerInventory` lists all six applications and fails if any
directory disappears, forcing a deliberate update rather than a silent stale
list. It also asserts tenant-portal remains a known live caller.
