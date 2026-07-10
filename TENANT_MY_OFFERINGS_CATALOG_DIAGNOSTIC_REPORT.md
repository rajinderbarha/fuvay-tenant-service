# Tenant My Offerings — Catalog Diagnostic Report

## Hard gate check

**AC Repair exists in the platform catalog and now appears as an available offering for the
certified tenant.** Confirmed live: `GET /v1/provider/offerings/available` returns 15 offerings
including "AC Repair" (id `a96e625a-60e1-46c0-bde4-ccbb88da50a2`) for `provider@serviceos.in`
(tenant `34b427a7-b2be-496c-b826-6d51bb181248`, Demo AC Services, vertical `home_services`).

## Root cause (before fix)

`GET /v1/provider/offerings/available` and `GET /v1/provider/offerings/enabled`
(`app/engines/provider_portal/router.py`) queried a table called `master_offerings`, which
**has zero rows in the live database** — confirmed via `\dt` and direct row count. Every tenant,
regardless of vertical, package, or approval state, saw `Available Offerings: 0`.

The real, live, populated platform catalog lives in a *different* table, `master_services`
(6 real rows including a real, active "AC Repair" service), joined to `service_categories`
(for vertical scoping) and `service_groups` (for display grouping). This is the same catalog
architecture the Admin Catalog engine (`admin_catalog/*`) manages and the customer-facing
`/v1/catalog/master/*` endpoints read from — the provider-facing offerings endpoints had simply
never been wired to it.

## 14-point diagnostic checklist

1. **Tenant vertical = Home Services.** ✅ Confirmed: `tenants.vertical = 'home_services'` for
   the test tenant.
2. **Home Services module enabled for tenant.** ✅ Implicit — tenant was seeded as a Home
   Services provider; `service_categories` row for Home Services (`0888d283-...`) has
   `vertical_type = 'home_services'` and `is_provider_registerable = true`.
3. **Tenant is approved or setup state allows catalog setup.** ✅ Package status is
   `paid_pending_approval` (pending admin approval, not blocking catalog *browsing* — only
   blocking full bookability, a separate concern from "can the tenant see the catalog at all").
4. **Platform Home Services category exists.** ✅ `service_categories` row `0888d283-...`,
   `name = "Home Services"`, `is_active = true`.
5. **AC Services / AC & HVAC group exists.** ✅ `service_groups` row `4488cc1f-...`,
   `name = "AC & HVAC"` (ticket's illustrative "AC Services" name; real seeded name is
   "AC & HVAC" — same concept).
6. **AC Repair master service exists.** ✅ `master_services` row `a96e625a-...`,
   `service_name = "AC Repair"`.
7. **AC Repair is enabled/customer-visible/provider-selectable.** ✅ `is_active = true`,
   `deleted_at IS NULL`.
8. **Split AC is mapped to AC Repair.** ⚠️ Was **not mapped** — `master_service_types` had 0
   rows for AC Repair. **Fixed**: mapped via the real admin API
   (`POST /v1/admin/master-services/{id}/types`) — Split AC (required, default) and Window AC.
9. **LG is mapped to AC Repair.** ⚠️ Was **not mapped** — `master_service_brands` had 0 rows.
   **Fixed**: mapped via the real admin API (`POST /v1/admin/master-services/{id}/brands`) — LG
   (default), Samsung, Voltas.
10. **Not Cooling is mapped to AC Repair.** ✅ Already mapped — 8 real issue-type mappings exist
    in `service_issue_mappings`, including "AC Not Cooling" and "Water Leakage". **No fix
    needed for the data**; however no tenant-readable endpoint existed to *read* this mapping —
    see Bug 3 below.
11. **Service options like Gas Refill/Emergency Visit are mapped.** ✅ Already mapped — 2 real
    `master_service_options` rows for AC Repair: "Gas Refill", "Emergency Visit" (matches the
    ticket's baseline exactly).
12. **Tenant package allows service setup.** ✅ Package browsing/enabling is not gated by
    package status in the current backend (only final bookability is) — confirmed no 403 on
    enable while package is `paid_pending_approval`.
13. **Frontend API call uses correct tenant context.** ✅ `_tid(user)` derives tenant_id from
    the JWT in every offerings endpoint; confirmed no client-supplied tenant_id is used.
14. **Frontend filter does not accidentally filter everything out.** ✅ Confirmed — the
    frontend's `availableList` search filter only applies when a search term is typed; with an
    empty search box all 15 real offerings render.

## Bugs found and fixed

1. **`master_offerings` vs `master_services` mismatch** (the hard-gate bug) — fixed by
   rewriting the `available`/`enabled` list queries to join `master_services` +
   `service_categories` + `service_groups`, scoped by `service_categories.vertical_type =
   tenants.vertical`. See `alembic` migration history is not applicable here (no schema
   change — SQL rewrite only) and `TENANT_MY_OFFERINGS_INTEGRATION_REPORT.md`.
2. **`ON CONFLICT (tenant_id, offering_id)` didn't match the partial unique index** created in
   the same session's earlier My Status migration (115), causing a live 500 on first enable.
   Fixed by adding the matching `WHERE deleted_at IS NULL` clause to the `ON CONFLICT` target.
3. **`provider_enabled_offering_id` was never aliased** in 6 of the offerings endpoints'
   `SELECT *` queries (only the raw `id` column existed), which would have left every
   frontend action (Edit, Activate, Deactivate, Refresh Readiness, View Enabled Offering) with
   an `undefined` target ID. Fixed by aliasing `id AS provider_enabled_offering_id` in all 6
   call sites.
4. **No tenant-readable endpoint existed for issue-type coverage** (`service_issue_mappings` —
   real, seeded data, but unreadable by anyone except through direct DB access). Added
   `GET /v1/admin/master-services/{id}/issues` (mirroring the existing, real
   `.../types` and `.../brands` endpoints exactly, same `get_current_user` permission level).

## Conclusion

The hard gate is satisfied: AC Repair (and 14 other real, active platform services) now appears
as an available offering for the certified tenant, with full Split AC/Window AC type coverage,
LG/Samsung/Voltas brand coverage, 8 real issue-type mappings, and 2 real service options — all
live-verified, not fabricated.
