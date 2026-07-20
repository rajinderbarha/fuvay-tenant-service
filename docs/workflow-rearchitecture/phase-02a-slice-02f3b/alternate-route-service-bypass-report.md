# Alternate Route and Service-Layer Bypass Report — Workstream 9

## Scope
Services and handlers directly connected to the 27 reachable mutations
across the 3 audited modules.

## Alternate routes
The only alternate-route finding this slice's scope covers is the
accept/reject shadowing, fully resolved in `shadowed-route-closure.md`
(Workstream 2). No other alternate route exposing the same ServiceJob
mutation with weaker authorization was found:
- Whole-job cancel (`execution.home_service_router`) vs. assignment-cancel
  (`home_service_assignment.provider_router`) remain confirmed-distinct
  operations (Slice 2F-3A finding, re-confirmed unchanged this slice).
- No `field_ops` Job route exposes any of these 27 capabilities (confirmed
  via Slice 2F-3A's audit, not re-derived from scratch this slice).

## Service-layer bypasses
`execution.home_service_router` has no separate service class exposed to
any other router — `HomeServiceJobExecutionService` and
`AdminJobActionsService` are only instantiated inside this router.
`home_service_assignment`'s `HomeServiceJobAssignmentService` is
instantiated by both `staff_router` and `provider_router` (both audited
this slice) — no third caller was found (grepped `app/` for
`HomeServiceJobAssignmentService(` outside these two files: zero matches).

## Direct database mutations
All mutations in all 3 modules go through their respective service classes
or (for a few `execution.home_service_router` admin actions) directly via
`AdminJobActionsService` — no in-handler raw SQL `UPDATE`/`DELETE` was
found bypassing these service layers in any of the 27 endpoints (unlike
`provider_portal.router`, which used raw SQL directly — a different
pattern, confirmed by reading the router source).

## Closed this slice
- The accept/reject shadow (via decorator removal, not a service change).
- The tenant defense-in-depth gap in `technician_accept_job`/
  `technician_reject_job` (via the new optional `tenant_id` parameter).

## Not claimed
This is not a repository-wide service-layer audit — scoped exclusively to
methods and handlers directly connected to these 3 modules' 27 reachable
mutations, per the mission's explicit instruction.
