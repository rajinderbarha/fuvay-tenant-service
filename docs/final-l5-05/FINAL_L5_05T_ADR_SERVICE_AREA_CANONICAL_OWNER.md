# FINAL-L5-05T — ADR: Service Area Canonical Owner

## Decision

`app.engines.serviceability.service.ServiceabilityService` /
`app.engines.serviceability.router` is the certified canonical owner of
Tenant Service Areas — both the admin-facing family
(`/v1/admin/tenants/{tenant_id}/service-areas*`) and the tenant-portal
self-service family (`/v1/tenant/service-areas*`).

`app.engines.tenant_engine.admin_service.AdminTenantService`'s
list/create/update/delete_service_area methods, and the routes in
`tenant_engine.admin_router` and `tenant_engine.portal_router` that called
them, are removed entirely.

## Evidence

### 1. Runtime reachability (the dispositive fact)

`app/main.py` registers `serviceability_router` (line 166) before
`admin_tenant_router`/`tenant_portal_router` (line ~363). FastAPI resolves
the first matching route for a given `(method, path)`. Confirmed via the
live, running application's actual route table (not source inspection):
before this sprint's fix, `GET`/`POST`/`DELETE` on both the admin and
tenant-portal service-area paths were **exclusively** handled by
`serviceability.router` — the identical `tenant_engine` handlers were
already unreachable dead code (established in FINAL-L5-05Q for the admin
path; this sprint additionally discovered and confirmed the same is true
for the previously un-inventoried tenant-portal path).

### 2. A second, undiscovered live mutation path (not caught by 05Q)

FINAL-L5-05Q's own framing described the duplication as "identical route,
one side dead." Runtime inventory this sprint found that was incomplete:
the "update" operation was registered under **different HTTP verbs** on
each side — `serviceability.router` uses `PUT`, `tenant_engine.admin_router`
and `tenant_engine.portal_router` both used `PATCH`. Different verbs on the
same path do not collide in FastAPI's router — both were live and
independently reachable. The `PATCH` path bypassed all of
`ServiceabilityService.update_service_area`'s validation (coverage-type/
geography validation, duplicate-check on update, `is_primary` reassignment)
while still being tenant-safe (proper `WHERE tenant_id = ... AND id = ...`
scoping) and — notably — the only one of the two writing an audit event.
This was a real, live, exploitable second mutation surface with weaker
validation than the canonical path, undiscovered until this sprint's
Part 2 runtime inventory.

### 3. Domain cohesion and feature completeness

`serviceability` is a strictly larger, more complete implementation:

| Capability | serviceability | tenant_engine (removed) |
|---|---|---|
| Admin CRUD (list/create/update/delete) | ✅ | ✅ (shadowed/duplicate) |
| Tenant self-service CRUD | ✅ (`/v1/tenant/service-areas`) | ✅ (shadowed/duplicate) |
| Coverage-type validation (city/zipcode/zone/radius) | ✅ (`_validate_coverage`) | ❌ (only a 4-value enum check) |
| Zone (`zone_id`) support | ✅ | ❌ |
| Lat/long support | ✅ | ❌ |
| `is_primary` reassignment | ✅ | ❌ |
| Duplicate-check on update (not just create) | ✅ | ❌ (create only) |
| Plan-limit enforcement (`get_service_area_limits`) | ✅ | ❌ |
| Candidate validation before save (`validate_service_area`) | ✅ | ❌ |
| Nested service-mapping (`/{area_id}/services`) | ✅ | ❌ |
| Cross-tenant ownership check (admin path) | ✅ (FINAL-L5-05Q) | ✅ (defense-in-depth, dead) |
| Advisory-lock duplicate-creation guard | ✅ (FINAL-L5-05Q) | ✅ (defense-in-depth, dead) |
| Audit trail | ❌ (fixed this sprint) | ✅ (dead code) |

`serviceability` also explicitly documents its comment in `main.py`
("Serviceability Engine — must mount before Booking (preflight depends on
it)") establishing that the booking/matching engine's serviceability
preflight check already depends on this exact table via this exact
service — real, load-bearing domain cohesion that `tenant_engine` (a
general-purpose ~3000-line admin CRUD router spanning users, staff,
wallet, deposit, offerings, and more) does not have.

### 4. Frontend already treats serviceability as canonical

`frontend/tenant-portal/lib/api.ts`'s `serviceAreaApi` calls `PUT` (not
`PATCH`) for update and consumes `limits`/`validate` — endpoints that only
exist on `serviceability`. This client was evidently built against the
canonical implementation already, with zero reliance on any
`tenant_engine`-only capability. `frontend/super-admin/lib/api.ts`'s admin
client had response-shape bugs (see below) that only make sense if it was
originally built against the (dead) `tenant_engine` contract's field names
(`area_id`, `area_type`) and never updated once `serviceability` became
the live handler — further confirming `serviceability` was already the de
facto runtime owner, just with an un-reconciled frontend contract.

## Rejected alternative: `tenant_engine` as owner

Rejected. Would require porting `serviceability`'s entire richer feature
set (coverage validation, zone/geo fields, primary-area management,
update-time duplicate checking, plan limits, candidate validation, nested
service mappings, the booking-preflight dependency) into a general-purpose
admin CRUD router that has no other reason to own this domain. Far larger
migration effort for zero benefit, and would break the booking/matching
engine's real dependency on `serviceability`'s specific service class.

## Rejected alternative: a new dedicated coverage engine

Rejected as out of this mission's bounded scope. `serviceability` already
functions as exactly this — a dedicated engine for addresses, service
areas, and coverage matching. Introducing a third engine would be a net
new architecture decision, not a canonicalization of what already exists.

## Missing-behavior migration

The one real gap in the canonical implementation (zero audit events for
create/update/deactivate — confirmed via source read before this sprint)
was ported from the shadow implementation's `_audit()` pattern into a new
`ServiceabilityService._audit_service_area()` helper, writing
`SERVICE_AREA_CREATED` / `SERVICE_AREA_UPDATED` / `SERVICE_AREA_DEACTIVATED`
via the same `record_platform_audit()` primitive used platform-wide.
Live-verified: a real create/update/deactivate sequence produced 3 real
`platform_audit_logs` rows with `engine_id=serviceability`,
`entity_type=service_area`.

## Compatibility policy

No compatibility adapter was created. Verified before removal (Part 6/28):

- No test anywhere in the suite called the `tenant_engine` admin
  GET/POST/DELETE service-area routes or their backing service methods
  through anything other than direct-service-layer dead-handler tests
  (removed, see bug register L5-05T-006).
- No frontend caller anywhere in `frontend/super-admin` or
  `frontend/tenant-portal` called the `tenant_engine` `PATCH` update
  route — the tenant-portal frontend already used `PUT` (the canonical
  verb); the super-admin frontend had no update UI at all for this
  resource.
- Grep confirms zero remaining source references to the removed
  `AdminTenantService` service-area methods.

Since there is no real external or internal caller depending on the
shadow contract, a `TEMPORARY_COMPATIBILITY_ADAPTER` or `DEPRECATED_410`
disposition would add pure overhead with no protective value — `REMOVE`
was chosen per mission rule 19 ("compatibility adapters must be explicit
and temporary" implies they exist to protect a real caller; none existed
here).

## Permission policy (unchanged, explicit)

All 4 admin Service Area endpoints require `P.PLATFORM_ADMIN`, held only
by `super_admin` (via the `P.ALL` wildcard) — none of the 4 canonical
limited roles (`admin_operations`, `admin_finance`, `admin_security`,
`admin_readonly`) hold it, confirmed unchanged in
`app/core/permissions.py`. This sprint did not introduce a new permission
grant for Service Areas — that would be a genuine RBAC policy decision
(who should administer tenant coverage geography) outside this route-
canonicalization mission's bounded scope. Live-verified: Operations/
Finance/Security/Read-Only admins all correctly receive `403
PERMISSION_DENIED` for every Service Area operation, matching the
pre-existing, unchanged policy.

## Rollback plan

If a future need for the removed `tenant_engine` behavior emerges, the
git history (this commit and FINAL-L5-05Q's `b3ec4b0`) contains the full
prior implementation. Re-introducing it would require re-applying the
same shadowing analysis (registration order, verb collisions) rather than
blindly restoring the old code, since `serviceability` has since gained
new capability (the audit trail) the old shadow implementation never had
either.
