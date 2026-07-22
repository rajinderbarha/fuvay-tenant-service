# Held-Route Adjudication Contract

The two Set B routes (`POST /v1/geo/tenants/{tenant_id}/zones` /
`create_zone`, `POST /v1/geo/tenants/{tenant_id}/staff/{staff_id}/location`
/ `update_location`) share `GeoService` with the selected `delete_zone`
route but remain `PENDING_INDEPENDENT_OR_MODULE_LEVEL_ADJUDICATION` in the
56-route held registry.

**The future implementation slice must not silently close, add, or modify
either of these two routes.** If the same tenant-derivation fix applied to
`delete_zone` incidentally touches shared `GeoService` code paths that
`create_zone`/`update_location` also use, that slice must:

1. Document the shared-code overlap explicitly.
2. NOT extend the new tenant check to `create_zone`/`update_location`'s
   own authorization behavior without their own independent adjudication
   (the same discipline this slice applied to `MediaAccessService`/
   `MediaAssetService` in the N01 precedent — touch shared code only where
   direct evidence requires it for the SELECTED route, and never let that
   incidentally re-authorize an unadjudicated route).
3. Re-run this contract's held-status check to confirm both routes remain
   `PENDING_INDEPENDENT_OR_MODULE_LEVEL_ADJUDICATION` and non-canonical
   after its changes.
