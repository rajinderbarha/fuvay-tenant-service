# Alternate Serviceability Route Audit — Workstream 9

## Method
Searched `tenant_engine`, `provider_portal`, `admin_catalog`, `pricing`,
matching engines (`home_service_booking`), `booking`, `onboarding`,
provider setup, `geo`, and platform configuration for any equivalent
geography/coverage-mutation capability.

## Findings
`TenantServiceArea` is referenced (via import) in 6 other modules:
`admin_catalog.tenant_service`, `ai_conversation.backend_tools`,
`coaching_appointment.center_discovery`, `home_service_booking.matching_engine`,
`home_service_booking.provider_matching`, `real_estate_lead.provider_discovery`,
and `tenant_engine.admin_service`. **Every single one of these is a
read-only reference** (confirmed via grep for `TenantServiceArea(` as a
constructor call, and for `.add(TenantServiceArea` / `update(TenantServiceArea`
— zero matches across all of them). `admin_catalog.tenant_service` and
`tenant_engine.admin_service` use it only for dashboard-style `COUNT(*)`
statistics; the matching/discovery engines use it for read-only
candidate-tenant queries analogous to `serviceability`'s own matching
logic (each vertical — home services, coaching, real estate — appears to
have its own read path into the same coverage table, which is expected
given the different verticals' distinct matching needs, not a
duplicate write path).

## Disposition
**No alternate write path exists anywhere in the repository for
`TenantServiceArea` or `TenantServiceAreaService`.**
`app.engines.serviceability.service.ServiceabilityService` is the
**sole** writer of both tables — re-confirmed via a repository-wide
search for `.add(TenantServiceArea` / `.add(TenantServiceAreaService` /
any `update()`/`delete()` SQLAlchemy statement targeting either model
outside `serviceability/service.py`.

**Classification: CANONICAL_TENANT_COVERAGE_WRITE** (no
`ALTERNATE_PROTECTED`/`LEGACY_BLOCKED`/weaker path exists to classify —
there is exactly one writer, already fixed this slice).

## Conclusion
No weaker alternate route was found. This satisfies the mission's
requirement that "a weaker live mutation path must be fixed or block
approval" — there being no alternate path at all trivially satisfies it.
