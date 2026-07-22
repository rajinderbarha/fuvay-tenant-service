# Catalog Service Bypass Report — Workstream 12

## Methods audited
`enable_service`, `update_enabled_service`, `disable_service`,
`set_tenant_service_types`, `set_tenant_service_brands`,
`set_type_pricing`, `set_brand_pricing`, `publish_service`, `save_draft`.

## Callers
Every one of these methods has exactly one caller: the corresponding
endpoint in `admin_catalog/tenant_router.py`. Re-confirmed via the
alternate-route audit — no other module calls into
`TenantCatalogService`'s mutation methods.

## Tenant ID source verification (the fix)
`enable_service`/`disable_service` derive `tenant_id` via
`_require_tenant_id(tenant_id_raw)`, where `tenant_id_raw` comes from an
optional `tenant_id` query parameter. **Before this slice**, any
supplied `tenant_id_raw` was used unconditionally — a `tenant_owner`
(who legitimately holds `TENANT_UPDATE`) could pass a foreign tenant's ID
and mutate that tenant's catalog. **Fixed**: a non-platform actor's
supplied `tenant_id` must now match their own `actor_tenant_id`, or the
request is rejected with `PERMISSION_DENIED` (403). Platform roles
(`super_admin`, etc.) retain the ability to supply any `tenant_id` —
unchanged, since acting cross-tenant is their legitimate, by-design
capability.

The other 7 mutations derive tenant ownership via
`tenant_service_id` → `_load_tenant_service` → `_assert_tenant_owns_ts`
— no `tenant_id` override parameter exists on these routes at all, so
no equivalent bypass was possible there.

## Ownership verification
- `_assert_tenant_owns_ts` (MODULE-L5-03-hardened, pre-existing): applies
  uniformly to every tenant-scoped role, exempts only recognized platform
  roles — re-verified unmodified.
- `_assert_service_active`-equivalent checks (`MasterService.is_active`,
  `ServiceCategory.is_active`, category entitlement): all pre-existing,
  re-verified unmodified.

## Transaction boundaries
Each mutation performs its writes and `db.flush()`/commit within the
same request. No cross-request transaction spanning. No row/advisory
lock exists in `enable_service` (see `duplicate-concurrency-review.md`
for the documented, unfixed concurrency risk — the schema-level unique
constraint provides a hard backstop).

## Audit behavior
Not independently verified in exhaustive depth this slice (no audit-log
call was found in any of the 9 mutation methods via a targeted grep for
an equivalent `_audit`/`_log_event` pattern) — logged as a known
limitation, not fixed, consistent with the same disposition given to
similar audit-coverage gaps in prior slices (a design-choice, not a
mechanical fix).

## Service-layer defense-in-depth
Confirmed present and correct: `_assert_tenant_owns_ts` and (as of this
slice) the fixed `_require_tenant_id` both run inside the service layer
itself, independent of the router-level guard — genuine defense-in-depth.

## Conclusion
One directly-connected bypass found and fixed
(`_require_tenant_id`'s cross-tenant query-param override). No other
service bypass found. Audit-coverage gap logged as a known limitation.
