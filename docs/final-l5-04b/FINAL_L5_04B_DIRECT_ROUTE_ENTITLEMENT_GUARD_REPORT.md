# FINAL-L5-04B — Direct Route Entitlement Guard Report

## Real guard point: `TenantCatalogService.enable_service()`
The one concrete backend mutation guarded by entitlement this sprint: a tenant cannot enable (configure) a `master_service` unless it holds an ACTIVE category entitlement for that service's `service_group`. This is the mission's Part 12 (Service Setup Enforcement) and doubles as Part 11's proof point.

## Real test matrix (live curl, real backend, real database)
| Case | Result |
|---|---|
| Tenant lacks module entitlement | Not separately tested (module is a prerequisite for any category entitlement to exist at all — untestable in isolation without an invalid state) |
| Tenant has module but lacks category entitlement | **403 `CATEGORY_NOT_ENTITLED`** — live-tested: Tenant One (entitled to `ac_services` only) attempted to enable a `plumbing`-group service, got 403 |
| Entitlement inactive | Same mechanism — `has_category_entitlement` checks `status=='ACTIVE'`, an INACTIVE row is treated identically to no row |
| Entitlement expired | `_is_effective()` checks `effective_until` — not live-tested this sprint (no seeded row has an expiry date), but unit-covered by the underlying logic |
| Category globally inactive | Not layered into this specific guard — deliberately deferred (see Admin API Report's #4 gap) |
| Tenant Read Only accesses mutation route | Not re-tested this sprint (pre-existing, unrelated to entitlement; `enable_service` already required `P.TENANT_UPDATE` permission before this sprint) |
| Tenant A uses Tenant B category URL | N/A for this specific endpoint (no cross-tenant URL parameter exists — `tenant_id` is derived from the caller's own JWT, not a path/query parameter) |

## Positive case also verified (not just the negative)
Tenant One enabling an `ac_services`-group service (its real entitlement) succeeded with **201**, proving the guard doesn't over-block legitimate, entitled operations.

## Critical requirements
| # | Requirement | Result |
|---|---|---|
| 1 | Protected content must not flash | N/A for this endpoint (pure API mutation, no page render) |
| 2 | Backend must enforce entitlement | **Confirmed** — this is a real backend check, not a frontend-only hide |
| 3 | Frontend guard must reflect backend result | Not built this sprint — the tenant portal's Service Setup page does not yet show a pre-emptive "not entitled" state; a user would only discover the 403 on submit. Real gap. |
| 4 | LocalStorage state alone cannot grant entitlement | **Confirmed structurally** — entitlement is resolved server-side from the database on every request, never trusted from client-supplied state |
| 5 | Entitlement checks occur before mutations | **Confirmed** — the check runs before the `TenantService` row is created/re-enabled, not after |

## Result
One real, concrete, live-tested backend enforcement point exists (service enablement). Both the positive (entitled → succeeds) and negative (not entitled → 403) cases are proven with real HTTP calls against a real database. Broader route-guard rollout across every tenant-scoped mutation endpoint was not attempted this sprint (bounded scope) — see Remaining Blockers.
