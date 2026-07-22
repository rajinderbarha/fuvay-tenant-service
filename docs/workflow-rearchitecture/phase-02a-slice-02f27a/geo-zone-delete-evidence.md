# DELETE /v1/geo/zones/{zone_id} - Evidence (Slice 2F-27A)

- Mounted: yes, single instance, app.engines.geo.router:55, endpoint delete_zone.
- Guard: require_permission(P.TENANT_UPDATE).
- Request: zone_id from path. NO tenant_id anywhere.
- Service: GeoService.delete_zone(zone_id) - `SELECT ServiceZone WHERE id==zone_id`;
  if not found -> 404; else deletes and clears a redis pin. Genuine mutation.
- Ownership: NONE. The zone is addressed by id alone with no tenant/ownership
  predicate. Any TENANT_UPDATE holder can delete any zone by id (cross-tenant).
- Canonical/matrix: absent from both (verified). No alias route.
- Final protection: PERMISSION_ONLY_NOT_SCOPE_AWARE (UNPROTECTED). NOT
  FULLY_PROTECTED. Higher cross-tenant risk than Route A (no scoping at all).
