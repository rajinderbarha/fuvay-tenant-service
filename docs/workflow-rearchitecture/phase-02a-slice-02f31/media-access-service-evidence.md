# MediaAccessService Evidence - Slice 2F-31

Read, re-verified, and **not modified**.

`assert_can_delete(actor, asset)`:
- `super_admin` bypasses.
- Otherwise calls `assert_can_view(actor, asset)` first ("must be able to view
  to delete").
- Additionally: `customer` role may only delete media where
  `asset.uploaded_by_user_id == actor.user_id`.

`assert_can_view(actor, asset)`:
- `super_admin` bypasses; public assets are viewable by anyone authenticated.
- Customer-context assets: customer must own it, OR a tenant-side role
  (`tenant_owner`/`staff`/`technician`) may view within `actor.tenant_id ==
  asset.tenant_id`.
- Tenant-scoped assets: same-tenant required (verified in source, continues
  past the excerpt shown in earlier discovery).

This chain is the reason Set A's `POST /v1/media/{media_id}/replace` did not
need a service-layer change - `assert_can_replace` (in `MediaAssetService`)
already calls into this policy. The gap on Set A routes was exclusively at the
route-guard layer (access scope), never at the object-ownership layer.
