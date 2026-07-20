# Connected Service-Layer Audit — Workstream 10

## Scope and method
`provider_portal.router` does not use a separate service class — every
mutation executes raw parameterized SQL (`db.execute(text(...))`) directly
inside the route handler (confirmed by reading every one of the 24
endpoints; no `from app.engines.provider_portal.service import ...` or
equivalent import exists in this router). This means there is no separate
service-layer module to audit for alternate callers with a weaker guard —
**the router IS the service layer for this module**.

## Enumerate callers of the underlying tables
Grepped the whole `app/` tree for direct writers to
`provider_team_members`, `provider_availability_rules`,
`tenant_availability_exceptions`, `tenant_booking_window_settings`,
`provider_enabled_offerings`, `tenant_service_area_services`,
`provider_visibility_statuses` outside `provider_portal/router.py`:

- No other engine module writes to any of these 7 tables. Several read
  from them (`app/engines/analytics/provider_analytics.py`,
  `app/engines/home_service_assignment/staff_model.py`,
  `app/engines/home_service_booking/matching_engine.py` — all read-only
  consumers for matching/analytics purposes, confirmed via grep for
  `INSERT`/`UPDATE`/`DELETE` against these table names, zero matches
  outside this router).

## Internal / worker callers
None found — no Celery task, cron job, or background worker was found
writing to any of these 7 tables.

## Conclusion
**No service-layer bypass exists for this module** — there is no separate
service layer to bypass, and no other code path writes to any table this
module owns. The 3 real bugs this slice found and fixed (cross-tenant
read-back leaks, missing session revocation on deactivation) were located
directly inside the router handlers themselves, not in a separate,
alternately-callable service method — closing them in the router was the
complete fix, with no further alternate caller to chase.

This audit's scope is limited to services/tables reachable from this
module's mounted mutations, per the brief's explicit instruction — it does
not claim every repository service class was reviewed.
