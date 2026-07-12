# FINAL-L5-05T — Service Area Route Canonicalization, Dead-Code Removal and Route Uniqueness Certification

## Scope actually completed this sprint

FINAL-L5-05Q identified that `serviceability.router` and
`tenant_engine.admin_router` both registered the identical path
`/v1/admin/tenants/{tenant_id}/service-areas`, and fixed the real
cross-tenant vulnerability + concurrency bug on the actually-live
`serviceability` path, but explicitly left the duplicate-route
architecture itself unresolved. This sprint's mission: pick one canonical
implementation, remove or retire the shadow, reconcile behavior, and add
automated guards so the duplication cannot silently return. See
`FINAL_L5_05T_ADR_SERVICE_AREA_CANONICAL_OWNER.md` for the full decision
record.

### 1. Runtime inventory found the duplication was worse than 05Q's own framing

Two real gaps in FINAL-L5-05Q's own investigation, found via this
sprint's Part 2 runtime route inventory:

- **A second, parallel duplicate-route family existed on the tenant-portal
  side** (`/v1/tenant/service-areas`, `serviceability.router` vs.
  `tenant_engine.portal_router`) that 05Q never inventoried at all — only
  the admin-side duplication was documented.
- **The "update" operation was never actually shadowed on either side** —
  `serviceability.router` registers `PUT` for the item path;
  `tenant_engine.admin_router`/`portal_router` both registered `PATCH` for
  the same path. Different HTTP verbs don't collide in FastAPI's router,
  so `PATCH` was a second, live, independently-reachable mutation path
  this whole time, bypassing `serviceability`'s coverage validation,
  update-time duplicate check, and `is_primary` reassignment logic — a
  real, previously-undiscovered gap in validation coverage, though it was
  tenant-safe (proper `WHERE` clause) and, notably, the only one of the
  two paths that wrote an audit event.

### 2. Canonical owner decided: `ServiceabilityService`

Full evidence, rejected alternatives, and compatibility policy in the ADR.
Summary: `serviceability` is the actually-live implementation, has a
strictly larger and more correct feature set (coverage/geo validation,
zone support, `is_primary` reassignment, update-time duplicate checking,
plan limits, candidate validation, nested service mappings), and has a
real domain dependency from the booking/matching preflight engine. The
only capability the shadow implementation had that the canonical one
lacked was an audit trail — migrated (see below).

### 3. Missing behavior migrated: audit trail

`ServiceabilityService` wrote **zero** audit events for
create/update/deactivate before this sprint (confirmed via source read —
no `record_platform_audit` call anywhere in the file). The shadow
`AdminTenantService` implementation, despite being dead HTTP-unreachable
code on the admin side, did have a real audit trail via its `_audit()`
helper. Ported into a new `ServiceabilityService._audit_service_area()`
method, called from `create_service_area`/`update_service_area`/
`deactivate_service_area` with the mission's canonical event names
(`SERVICE_AREA_CREATED`/`SERVICE_AREA_UPDATED`/`SERVICE_AREA_DEACTIVATED`).
Live-verified: a real create→update→deactivate sequence produced 3 real
`platform_audit_logs` rows.

### 4. Shadow implementation removed entirely (not deprecated, not adapted)

- `tenant_engine/admin_router.py`: all 4 service-area routes
  (`GET`/`POST`/`PATCH`/`DELETE`) removed.
- `tenant_engine/portal_router.py`: all 4 service-area routes removed.
- `tenant_engine/admin_service.py`: the 6 backing methods removed
  (`list_service_areas`, `create_service_area`, `update_service_area`,
  `delete_service_area`, `_load_area`, `_area_dict`).

Disposition: `REMOVE`, not `DEPRECATED_410`/`TEMPORARY_COMPATIBILITY_ADAPTER`
(mission Part 19). Verified before removal that no compatibility bridge
was needed: no test called these routes except direct dead-handler
service-layer tests (removed, see bug register), no frontend caller used
the `PATCH` verb anywhere (the tenant-portal frontend already called
`PUT`, matching the canonical verb), and `git grep` confirms zero
remaining source references to the removed methods.

### 5. Global duplicate-route detector built (Part 22)

`tests/test_final_l5_05t_service_area_route_canonicalization.py`'s
`TestGlobalDuplicateRouteDetector` walks the **real, live FastAPI route
table** (not source-text grep) — this required discovering and working
around a real gotcha: `app.routes` in this FastAPI version contains
`_IncludedRouter` wrapper objects, not a flat list of `APIRoute` — a naive
`isinstance(r, APIRoute)` filter silently sees 0 routes and every
"duplicate route" check built on it is a false negative. A recursive
flattener (`_flatten_routes`) walks `_IncludedRouter.original_router.routes`
to get the real, complete route table (2,295 routes).

**A significant, unexpected byproduct finding**: once route flattening
was fixed, the detector found **18 real, pre-existing, app-wide
(method, path) duplicate-route registrations completely unrelated to
Service Areas** — spanning Customer Addresses, Engine Health, Finance
Summary, Tenant Wallet, Service Options, Staff Job Accept/Reject, and
Analytics Alerts (full list in the bug register, L5-05T-013). Each one
means a handler is silently shadowed dead code, the exact same defect
class this sprint fixed for Service Areas. **Not fixed this sprint** —
explicitly outside the mission's bounded scope ("Do not alter broader
Provider branding, pricing, Jobs, Finance, Export or booking architecture
unless a real Service Area dependency requires a bounded compatibility
change" — none of these 18 touch Service Areas). Logged as a new P0/P1
finding for a dedicated future sprint. The detector enforces zero
tolerance for Service Area duplicates (never allowlisted, per mission
rule 24/29) while allowlisting the 18 pre-existing, out-of-scope ones by
exact `(method, path)` tuple with an explanatory comment — an additional
guard (`test_pre_existing_allowlist_still_matches_reality_exactly`)
ensures the allowlist can neither hide a new duplicate nor go stale.

A parallel duplicate-**operation-ID** detector found 13 more pre-existing,
unrelated duplicates (`admin_catalog.service_option_admin_router`,
`service_setup.templates_router`) — same treatment: documented,
allowlisted by module, Service Area confirmed never present.

### 6. Route ownership registry + OpenAPI uniqueness (Parts 24/23/37)

`TestRouteOwnershipRegistry` proves, against the live route table, that
`serviceability.router` is the exclusive owner of every
`/v1/admin/tenants/{tenant_id}/service-areas*` and `/v1/tenant/service-areas*`
path, and that `tenant_engine.admin_router`/`portal_router` register zero
service-area routes. `TestOpenAPIUniqueness` verifies the live-generated
OpenAPI schema exposes exactly one operation per canonical path/method
and that `PATCH` never appears again on the admin/portal item paths.
Live-verified against the running server's real `/openapi.json`:
```
/v1/admin/tenants/{tenant_id}/service-areas          [GET, POST]
/v1/admin/tenants/{tenant_id}/service-areas/{area_id} [PUT, DELETE]
/v1/tenant/service-areas                              [GET, POST]
/v1/tenant/service-areas/{area_id}                    [GET, PUT, DELETE]
/v1/tenant/service-areas/limits                       [GET]
/v1/tenant/service-areas/validate                     [POST]
/v1/tenant/service-areas/{area_id}/set-primary        [POST]
/v1/tenant/service-areas/{area_id}/services            [GET, POST]
/v1/tenant/service-areas/{area_id}/services/{mapping_id} [PUT, DELETE]
```
All unique operation IDs, confirmed via the live schema.

### 7. Include-order safety (Part 21)

Since exactly one module now owns every Service Area path (proven above),
route selection cannot depend on `main.py`'s include order any more —
`TestIncludeOrderSafety` makes this invariant explicit rather than
relying on the previous, fragile "serviceability happens to be registered
first" ordering dependency.

### 8. Frontend contract reconciliation (Parts 17/18) — 3 real, live bugs found and fixed

Investigating the frontend callers surfaced genuine, previously-unknown
bugs, not just a missing type update:

- **`adminTenantApi.listServiceAreas`/`deleteServiceArea`** (super-admin
  `lib/api.ts`) were dead client code — never called anywhere in the app.
  Removed.
- **`adminTenantApi.createServiceArea`**'s response type (`AdminServiceArea`,
  keyed `area_id`) never matched the real, live response (`id`, via
  `TenantServiceArea.to_dict()`) — it matched the *removed shadow
  implementation's* field names instead. The type evidently was never
  updated once `serviceability` became the live handler. Fixed: retyped
  to the corrected `AdminTenantServiceArea` interface.
- **`AdminTenantServiceArea`** (used by `adminProviderEnablementApi.listServiceAreas`,
  which powers the real, rendered "Provider Coverage Areas" tab on
  `/admin/tenants/[id]`) had 2 of 10 columns silently broken in
  production: the "Type" badge read `a.area_type` (doesn't exist on the
  real response, real key is `coverage_type`) and every table row's React
  `key` was `a.area_id` (doesn't exist, real key is `id`) — every row
  showed a blank Type badge and every row had an `undefined` React key
  (a real, live rendering defect, not a hypothetical one). Fixed: field
  names corrected to match the real response exactly; list-wrapper key
  fixed from `count` to `total` (also wrong).
- **A real wrong-refetch bug**: after successfully creating a Service Area
  via the "Add Service Area" modal, the success handler called
  `zones.refetch()` — the **unrelated Geo Zones data source**
  (`/v1/geo/tenants/{id}/zones`, a completely different table/feature) —
  instead of refetching the actual Provider Coverage Areas list. A newly
  created service area never appeared in the UI without a full page
  reload. Fixed: introduced a `refreshToken` prop threaded from the
  parent page into `ProviderAreasTab`, bumped on successful creation, so
  the correct list actually refetches.

The tenant-portal frontend (`frontend/tenant-portal/lib/api.ts`) needed
**no changes** — it was already correctly built against `serviceability`'s
real contract (`PUT` for update, `{areas, total}` response shape, `id`-keyed
items, and use of `limits`/`validate` endpoints that only exist on the
canonical implementation) — further evidence `serviceability` was already
the de facto runtime owner in practice, just with an un-reconciled admin
frontend contract.

## Automated guards added

`tests/test_final_l5_05t_service_area_route_canonicalization.py` — 25
new tests: global duplicate-route detector (app-wide + Service-Area-
specific zero-tolerance), duplicate-operation-ID detector, route
ownership registry (4 tests), include-order safety (2), dead-code removal
verification (4), canonical audit-trail verification (4), OpenAPI
uniqueness (2), and 2 real-Postgres concurrency tests extending
FINAL-L5-05Q's create-vs-create coverage with update-vs-deactivate and
cross-tenant independence.

`tests/test_final_l5_05q_provider_coverage_mutations.py` — updated in
place: `TestDuplicateRouteRegistrationFinding`'s stale "both routers still
define the path" assertion replaced with its inverse (pins the absence);
`TestAdminTenantServiceDefenseInDepthFixesStillCorrect` (which pinned
source text that no longer exists) replaced with
`TestAdminTenantServiceServiceAreaMethodsRemoved`.

`tests/test_sprint4_tenant_onboarding.py` — 5 dead-handler tests removed
(`test_list_service_areas_empty`, `test_create_service_area_missing_city`,
`test_create_service_area_invalid_type`, `test_delete_service_area`,
`test_service_area_not_found` — all called the now-removed
`AdminTenantService` methods directly); `test_portal_router_has_service_areas_route`
inverted to assert absence; the now-orphaned `_make_area()` test helper
removed.

`tests/test_serviceability_hardening.py` — `make_db()` fixture gained
`db.flush = AsyncMock()` (the audit-porting change added a `db.flush()`
call before the audit write to ensure `area.id` is populated; the shared
mock fixture didn't have it mocked, caught immediately by the existing
test suite).

## Verification summary

- **Runtime route inventory**: complete — 2,295 total routes flattened
  and inspected; exactly one module (`serviceability.router`) owns every
  Service Area path; the previous admin-side AND tenant-portal-side
  duplicates both confirmed eliminated.
- **Live backend startup**: real Postgres + real backend started fresh
  with this sprint's code; health check passes; OpenAPI loads with the
  exact expected 9 canonical Service Area paths, zero `PATCH` on either
  item path.
- **Live 5-role authorization matrix**: Super Admin — list/create/update
  all `200`/`201`, duplicate create correctly `409 DUPLICATE_SERVICE_AREA`.
  Operations/Finance/Security/Read-Only Admin — all correctly `403
  PERMISSION_DENIED` on every operation tested (unchanged, pre-existing
  `P.PLATFORM_ADMIN`-only policy, not modified this sprint — see ADR).
- **Live cross-tenant matrix**: a real Tenant A service area accessed via
  Tenant B's admin route for both `PUT` and `DELETE` both correctly
  returned `404` with zero mutation (verified: the area was still
  successfully deletable via the correct tenant's route afterward,
  proving the cross-tenant attempts made no change).
- **Live audit verification**: direct database query after the live
  matrix confirmed real `SERVICE_AREA_CREATED`/`UPDATED`/`DEACTIVATED`
  rows in `platform_audit_logs` with `engine_id=serviceability` —
  previously would have been zero rows.
- **Real concurrency verification**: 2 new real-Postgres tests (update-vs-
  deactivate racing on the same row with no lost update; two distinct
  tenants creating identical geography concurrently, proving the
  tenant-scoped advisory lock key doesn't serialize unrelated tenants) —
  both pass, extending FINAL-L5-05Q's existing create-vs-create coverage.
- **Backend regression**: full suite `9253 passed, 1 skipped, 0 failed`
  (baseline before this sprint: 9233 passed — net +20 after removing 6
  dead-handler tests and adding 25 new 05T tests plus test-count
  fluctuation in the updated 05Q file).
- **TypeScript**: `0` errors.
- **Production build**: passes, including `/admin/tenants/[id]`.
- **OpenAPI live verification**: fetched from the running server, parsed
  directly — confirmed against the exact expected path/method/operation-ID
  set (see above).

## Explicitly not attempted this sprint (honestly documented, not hidden)

See `FINAL_L5_05_BUG_REGISTER.md` (L5-05T-001 through 013) and
`FINAL_L5_05_REMAINING_BLOCKERS.md`. In summary:

- **18 pre-existing, unrelated app-wide duplicate-route registrations**
  (Customer Addresses, Engine Health, Finance Summary, Tenant Wallet,
  Service Options, Staff Job Accept/Reject, Analytics Alerts) were
  discovered as a byproduct of building this sprint's global detector.
  Each is the same defect class as the Service Area duplication this
  sprint fixed — **not fixed here**, explicitly outside this mission's
  bounded scope, allowlisted with justification and pinned so the
  allowlist itself cannot silently grow. This is a significant new
  finding for a dedicated future sprint.
- **13 pre-existing, unrelated duplicate operation IDs** (admin_catalog
  service-option config, service_setup templates) — same treatment.
- **No Chromium/browser-automation verification was performed** — no
  browser automation tool was available in this session (same limitation
  documented in FINAL-L5-05S). All verification is real, live HTTP/API
  evidence (curl against the running backend with real logins, real
  cross-tenant substitution, real database audit-row confirmation) rather
  than fabricated or silently skipped.
- **Formal performance benchmarking** (Part 40: query counts, latency
  measurements, lock-wait timing) was not run as a dedicated benchmark
  pass — the concurrency tests prove correctness (no lost updates, no
  false serialization across tenants) but do not produce timing numbers.
- **The Operations Admin explicit-policy question** (mission Part 10:
  "Operations Admin follows explicit policy") was resolved as "no change"
  — the pre-existing `P.PLATFORM_ADMIN`-only gate is preserved exactly as
  it was, since introducing a new permission grant for Service Area
  administration is a genuine RBAC product decision outside a route-
  canonicalization mission's bounded scope, not a routing defect.

## Result

The mission's core charter is complete and live-verified: exactly one
Service Area implementation exists and is reachable
(`ServiceabilityService`/`serviceability.router`), the shadow
implementation is removed (not just unregistered — the routes, backing
service methods, and dead-handler tests are all gone), the one real
missing-behavior gap (audit trail) was migrated into the canonical path
and live-verified, a real second live mutation path this sprint
discovered (`PATCH` on both the admin and tenant-portal sides) is closed,
a global duplicate-route/operation-ID detector now exists with zero
tolerance for Service Area duplication specifically, OpenAPI exposes
exactly one operation per canonical path, and 3 real, previously-unknown
frontend contract bugs (wrong field names on 2 of 10 rendered columns,
a wrong-endpoint refetch preventing newly created areas from appearing)
were found and fixed. The tenant-isolation and concurrency protections
from FINAL-L5-05Q are fully preserved and additionally extended with 2
new real-Postgres tests. The most significant new finding beyond this
mission's own stated scope is architectural: 18 more pre-existing,
unrelated app-wide route duplications and 13 more duplicate operation
IDs exist in this codebase, following the exact same defect pattern this
sprint fixed for Service Areas — honestly documented as a new blocker for
a dedicated future sprint rather than expanded into or silently ignored.
