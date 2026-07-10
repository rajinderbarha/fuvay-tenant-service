# Admin A3 — Tenant Management (List) Report

## Route
`frontend/super-admin/app/admin/tenants/page.tsx` (1043 lines) — pre-existing,
substantial, real-data implementation (from the `P0 Enterprise Tenants
Dashboard` sprint). Not rebuilt from scratch this sprint; verified and
extended.

## List capabilities confirmed real
- Columns (via `label:` literals): Tenant, Status, Verification, Vertical,
  Plan, Health, Location, Usage Credits, Jobs, Issues, Created, Actions.
- Search: free-text `q` param wired to `adminTenantsApi.list()`.
- Filters: status, verification_status, plan_type, city_tier, state,
  district, city, created_from/to.
- Sort: `sort_by`/`sort_direction` server-side.
- Pagination: `page`/`page_size`, server-side.
- Row actions (`RowActions` component): View Details, Open 360, Review
  Verification, Request Changes, Change Plan, Add Usage Credits, Send
  Notification, View Audit Logs, Suspend Tenant / Reactivate (conditional).

## Gaps confirmed and documented (not fixed this sprint)
1. No vertical / bookability / health-band / deposit / usage-credit-range
   filters in `adminTenantsApi.list()` params — ticket examples of filter
   types not all present.
2. Bulk "Suspend All" button is a non-functional stub (~line 917).

## Live data-accuracy check
`GET /v1/admin/tenants` against the real DB (1 real tenant row, "Demo AC
Services") returned the correct single row with `status='pending_setup'`,
`verification_status='pending'`, matching DB state exactly.

## Verdict
List module is real, functional, DB-backed. Two non-blocking gaps
documented in `ADMIN_A3_REMAINING_BLOCKERS.md`.
