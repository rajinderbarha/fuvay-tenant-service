# Selected Module Implementation Contract (WS10)

**This contract is not executed in this slice.** It is the frozen brief for
the future implementation slice that closes `geo_zone_management`.

## Selected module

`geo_zone_management` — `DELETE /v1/geo/zones/{zone_id}` (`delete_zone`)

## Exact A/B/C route lists and hashes

- Set A (implement): [selected-canonical-route-scope.csv](selected-canonical-route-scope.csv) — hash `fc45fa777f47c2c9`
- Set B (held, do not silently close): [selected-held-adjudication-scope.csv](selected-held-adjudication-scope.csv) — hash `593837fac1076324`
- Set C (do not touch): [selected-out-of-scope-adjacent-routes.csv](selected-out-of-scope-adjacent-routes.csv) — hash `578a7e506b83dc09`

## Allowed application files (to be discovered/confirmed exactly by the implementation slice, not assumed here)

- `app/engines/geo/router.py` — the `delete_zone` route handler and its
  `_svc()` dependency factory (to pass trusted actor tenant context, same
  pattern as `MediaService` in Slice 2F-31A).
- `app/engines/geo/service.py` (or wherever `GeoService` is actually
  defined — confirm via `inspect.getsourcefile`, do not assume the path)
  — add a tenant-authority check before the `delete_zone` query, following
  the `_require_trusted_tenant` pattern established in
  `app/engines/media/service.py` (Slice 2F-31A).
- `app/core/permissions.py` — ONLY if no existing guard fits; reuse
  `require_permission(P.TENANT_UPDATE)` (already in place) if it is
  sufficient once paired with the new service-layer check.

## Forbidden application files

- Any file outside the above, including but not limited to
  `app/engines/webhook/*` (Set C), any file backing the 23 other Set C
  routes, `app/engines/media/*` (N01 — already closed, do not reopen), and
  `GeoService.create_zone`/`update_location` (Set B — held, not
  authorized for this contract).

## Required guard pattern

Preserve `require_permission(P.TENANT_UPDATE)` (the existing role/
permission gate) — do not replace it. Add tenant authority at the service
layer, not by narrowing the route guard's admitted role set.

## Required service-layer authority

`GeoService` must derive the acting principal's tenant server-side (via
its constructor, from `UserContext`, the same shape as
`MediaService.actor_tenant_id`) and compare it to the zone's actual
`tenant_id` before any mutation — `ServiceZone.tenant_id` must be added to
the query predicate (currently absent entirely). Confirm
`ServiceZone` has a `tenant_id` column before writing the fix; if it does
not, this is a `IMPLEMENTATION_SCOPE_BLOCKED`-worthy discovery for that
slice to report, not to route around.

## Required tenant/object ownership

The query for `delete_zone` (and ideally `get_zone`/`update_zone`, though
only `delete_zone` is in Set A) must scope by `ServiceZone.id == zone_id
AND ServiceZone.tenant_id == actor_tenant_id` (or platform-admin bypass),
mirroring `WebhookService.delete_endpoint`'s existing tenant-filtered
query shape but with a VERIFIED tenant instead of a client-supplied one.

## Required privacy audit

Confirm foreign-tenant and missing-zone responses are indistinguishable
(no existence oracle), following the `NotFoundException`-for-both pattern
established in `MediaService`.

## Required state/domain audit

`delete_zone` is a soft state transition (`is_active = False`); confirm no
destructive/irreversible storage or cross-system side effect exists beyond
the best-effort Redis cache delete already present.

## Required caller audit

`git grep GeoService(` and `git grep '.delete_zone('` across `app/` to
confirm the router is the only caller, mirroring Slice 2F-31A's
`service-caller-graph.csv` methodology.

## Required tests

A new `tests/test_phase2f32_geo_zone_closure.py` (or equivalently named)
file with the same category structure as
`tests/test_phase2f31a_n01_residual_closure.py`: authorization, tenant/
object, service, privacy, negative controls for each. A dedicated verifier
script following the `verify_n01_2f31a.py` pattern, with a `--selftest`
negative-fixture proof.

## Coverage arithmetic rules

`final_protected = 238 + 1` (if `delete_zone` closes),
`final_denominator = 262` (unchanged), `final_unprotected = 262 -
final_protected`. No other canonical row may change guard_status. The
denominator must not change.

## Allowed final statuses

`SECURITY_CLOSED` (if fully closed on authorization/privacy/ownership
grounds), `SECURITY_CLOSED_DOMAIN_INTEGRITY_BLOCKED` (if a genuine
non-destructive integrity gap is found, following the 2F-31A precedent),
`IMPLEMENTATION_SCOPE_BLOCKED` (if `ServiceZone` lacks a `tenant_id`
column or the fix requires a file outside the allow-list),
`INCOMPLETE`.

## Stop condition

Stop at that slice's own approval gate once `delete_zone` is closed (or
correctly reported blocked). Do not select a further module. Do not touch
Set B or Set C routes.
