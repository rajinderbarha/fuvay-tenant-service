# Module Selection Decision (WS8)

## Selected module: `geo_zone_management`

**Route:** `DELETE /v1/geo/zones/{zone_id}` (`delete_zone`,
`app/engines/geo/router.py` + `GeoService`)

## Top-3 comparison

| Factor | geo_zone_management | webhook_endpoint_management | platform_commerce_deposit |
|---|---|---|---|
| 1. Security severity | **CRITICAL** — zero tenant predicate anywhere (route AND service) | HIGH — client-supplied tenant_id, never verified against actor | LOW-MEDIUM — service layer already asserts tenant ownership |
| 2. Cross-tenant/destructive impact | Any `TENANT_UPDATE` holder in ANY tenant can deactivate ANY other tenant's zone by ID | Any `TENANT_UPDATE` holder can delete another tenant's webhook by naming that tenant in the query string | Cross-tenant path already closed (`_assert_owns_tenant_deposit`) |
| 3. Credential/session/financial sensitivity | None | None | HIGH (security deposit) — but bounded by #1's finding |
| 4. Canonical route count | 1 | 1 | 3 |
| 5. Held-candidate uncertainty | 2 held routes share the boundary (`create_zone`, `update_location`) — noted, does not block | 0 | 0 |
| 6. Product-policy readiness | Ready — no blocker found | Ready | Ready |
| 7. Atomic closure feasibility | HIGH — single route, clear fix (derive tenant server-side, add predicate) | HIGH — single route, same fix shape | MEDIUM — 3 routes, but fix is narrower (access-scope guard only) |
| 8. Testability | HIGH — established `inspect.getsource`/live-route pattern | HIGH — same pattern | HIGH |
| 9. Dependency on unfinished work | None | None | None |
| 10. Risk reduction per slice | **HIGHEST** — closes the only completely unscoped cross-tenant destructive mutation in the remaining 24-route queue | HIGH | MEDIUM — real but narrower gap than the "financial" label implies |

## Why geo over webhook

Both are single-route, atomically closeable, and score similarly on
factors 4–9. Factor 1 (security severity) and factor 2 (cross-tenant/
destructive impact) — the two highest-priority factors per the mission's
explicit ordering — favor geo unambiguously: webhook's `delete_endpoint`
at least filters by a client-supplied `tenant_id` (an unverified value,
but a value); geo's `delete_zone` has **no tenant_id anywhere in the call
chain** — not even one to distrust. This was independently re-derived by
reading both routers and both services this slice, not carried forward
from any prior slice's ranking (the mission's WS6 explicitly warned
against preselecting geo/webhook "merely because previous documentation
ranked them highly" — this comparison rederives the ranking from source
and geo still comes out worse).

## Why not platform_commerce_deposit

Its "financial authority" label suggests high severity, but direct
inspection of `CommerceService._assert_owns_tenant_deposit` shows
cross-tenant access is already blocked at the service layer for all 3
deposit routes. The residual gap (missing access-scope awareness) is real
but narrower than geo's complete absence of any tenant check. This is
exactly the kind of finding the mission's WS5 instruction (ownership must
be inspected in the service, never inferred from route guards alone) is
meant to surface — a naive severity ranking by capability label alone
would have overrated this module and underrated geo.

## Why not a bundle

No two modules among the 24 share one service/authorization boundary, one
coherent file allow-list, and one atomic test/closure boundary — the
mission's explicit bar for bundling. `geo_zone_management` and
`webhook_endpoint_management` are the two closest in severity, but they
are different routers, different services, and different fix shapes
(geo needs a NEW tenant predicate; webhook needs the EXISTING predicate's
source changed from client-supplied to server-derived). Bundling them would
violate "one shared service/authorization boundary." Exactly one module is
selected: `geo_zone_management`.
