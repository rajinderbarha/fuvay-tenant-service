# Availability Ownership Decision — Workstream 7

## Finding: no per-technician self-service availability exists in this router
All availability-related tables reachable from `provider_portal.router`
(`provider_availability_rules`, `tenant_availability_exceptions`,
`tenant_booking_window_settings`) are **tenant-wide business configuration**,
not per-technician schedules:
- `provider_availability_rules` has a `scope_type`/`scope_id` pair
  (defaulting to `"provider"`) but no technician/user identity column, and
  every mutation is filtered purely by `tenant_id`, never by an acting
  technician's own identity.
- Every mutation endpoint touching these tables is gated by
  `require_tenant_owner_mutation` (role-restricted to `tenant_owner`/
  `super_admin`) — a `technician`-role principal cannot pass this guard at
  all, confirmed via direct HTTP test
  (`TestUnauthorizedRolesRejected::test_non_owner_role_rejected[technician]`).

## Answering the brief's 5 distinctions directly

1. **A technician updating their own availability** — does not exist in
   this router. If per-technician individual schedules are a desired future
   feature, they would need a new capability (new table/column linking a
   rule to a specific technician's `user_id`, plus a self-service permission
   distinct from `tenant_owner`-only) — not present today.
2. **Staff updating their own availability** — does not exist; no staff
   persona can reach any availability endpoint.
3. **Tenant owner changing business-wide hours** — this IS what every
   availability endpoint implements today (`create_availability`,
   `update_availability`, `delete_availability`, the exceptions endpoints,
   `apply_availability_preset`/`delete_availability_preset`,
   `update_booking_window`).
4. **Authorized manager changing another technician's schedule** — not
   applicable; there is no per-technician schedule for a manager to change.
5. **Bulk availability operations** — `apply_availability_preset` and
   `delete_availability_preset` are bulk operations (multiple rules
   created/deleted in one call), both correctly `tenant_owner`-gated and
   now access-scope-aware.

## Classification
All 9 availability-related mutation endpoints (`create_availability`,
`update_availability`, `delete_availability`,
`create_availability_exception`, `update_availability_exception`,
`delete_availability_exception`, `apply_availability_preset`,
`delete_availability_preset`, `update_booking_window`) are
**TENANT_OWNER_SELF_SERVICE** — "self-service" here meaning the tenant
owner managing their own business's configuration, not an individual
technician's personal schedule (no such concept exists in this router).

## Read-only must block
Yes — all 9 are now guarded by `require_tenant_owner_mutation`, which
blocks a read-only-scoped `tenant_owner` even with an explicit permission
override, directly HTTP-tested for all 9.

## Technician operational access
Not applicable to this router — technician-facing job/assignment schedule
concerns (if any) live in `execution.home_service_router` or
`home_service_assignment`, explicitly out of scope for this slice.
