# Module Selection Decision - Slice 2F-30

## Selected: `N01_media_assets` (`app.engines.media.new_router`) - 9 routes

| Route | Endpoint | Current guard |
|---|---|---|
| `DELETE /v1/provider/profile/logo` | remove_provider_logo | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE |
| `DELETE /v1/provider/profile/shop-photo` | remove_provider_shop_photo | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE |
| `DELETE /v1/staff/profile/photo` | remove_staff_profile_photo | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE |
| `POST /v1/me/profile-photo` | upload_my_profile_photo | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK |
| `POST /v1/media/upload` | upload_media | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK |
| `POST /v1/media/{media_id}/replace` | replace_media | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK |
| `POST /v1/provider/profile/logo` | upload_provider_logo | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE |
| `POST /v1/provider/profile/shop-photo` | upload_provider_shop_photo | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE |
| `POST /v1/staff/profile/photo` | upload_staff_profile_photo | ROLE_ONLY_NOT_ACCESS_SCOPE_AWARE |

## Rationale against the 10 criteria

1. **Security severity** - moderate (risk 10). The gap is real: every route
   lacks mutation-capable access-scope enforcement, so a tenant principal with
   a read-only `access_scope` can upload, replace and delete media.
2. **Cross-tenant / destructive** - bounded. `MediaAccessService` already
   enforces same-tenant on view/delete, so this is not an open cross-tenant
   deletion path. Verified by reading the service.
3. **Credential / financial sensitivity** - none.
4. **Route count** - **9 of 33 (27%)**, the largest remaining module.
5. **Held uncertainty** - 3 same-module candidates, all on the same
   MediaService boundary, adjudicated inside the slice. One of them
   (`DELETE /v1/media/tenants/{tenant_id}/files/{file_id}`) is a
   client-asserted-tenant delete - real value in adjudicating it here.
6. **Product readiness** - one minor blocker (whether provider logo/shop-photo
   deletion is owner-only or delegable). No new permission is required; the
   module is role-based today and stays role-based.
7. **Atomic closure** - one router, one service family, one access policy.
8. **Testability** - 3/3. Deterministic; no external gateway or worker.
9. **Dependencies** - none on unfinished modules.
10. **Risk reduction per slice** - highest by volume; it removes 27% of the
    remaining queue in one pass.

## Why the alternatives were not selected

- **N09_webhook_integration (priority 14, risk 13)** - ties on priority and has
  the **highest raw risk**: `WebhookService.delete_endpoint` scopes only to the
  *client-asserted* tenant, so a `tenant:update` holder can delete another
  tenant's endpoint. It is **1 route**. Selecting it would close 3% of the
  queue and leave the 9-route module for another cycle.
- **N10_geo_zones (risk 11)** - carries the single clearest defect in the whole
  queue: `GeoService.delete_zone(zone_id)` has **no tenant predicate at all**.
  Also 1 route.
- **N02_enterprise_grid_views (8/6)** - 6 routes but self-scoped grid
  personalization; low blast radius.
- **N05_security_deposit (10/3)** - highest financial dimension, but ownership
  is already enforced (`_assert_owns_tenant_deposit`), only 3 routes, and it
  carries 2 product blockers and 4 held candidates.

## Explicit trade-off, recorded

N09 and N10 have worse **per-route** defects than N01. They are single-route
modules, so a slice spent on either yields little queue reduction. The
recommendation is to run **N09 + N10 together as the immediate next slice** -
both are cross-tenant deletion defects, both have zero/low product blockers,
and together they are still only 2 routes. This slice selects N01 for leverage;
it does not claim N01 is the most dangerous module.

## Product decisions required

One, non-blocking: whether provider logo / shop-photo deletion is
tenant_owner-only or delegable to staff/technician. Until decided, implement
the narrower policy and record it.
