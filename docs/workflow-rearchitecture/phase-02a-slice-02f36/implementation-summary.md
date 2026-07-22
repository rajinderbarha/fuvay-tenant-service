# Slice 2F-36 Implementation Summary

Enterprise, Tenant-Administration and Operational Authorization Batch,
executed strictly against the frozen Slice 2F-34 artifacts in
`docs/workflow-rearchitecture/phase-02a-slice-02f34/`. Execution
container: 7 Set A modules + 10 held-registry modules, each with its own
scope/evidence/status.

## Set A (18 routes, 7 modules — all closed)

- `enterprise_grid_saved_views` (4): create/update/delete/set-default
  saved view
- `enterprise_grid_preferences_exports` (2): save column preferences,
  create export
- `admin_catalog_provider_setup` (4): set supported options, set
  supported brands, create brand request, provider setup recommendations
- `profile_technician_self_service` (3): update business profile, submit
  business profile for review, update staff profile
- `profile_universal_self_service` (1): update my profile
- `marketing_automation_provider` (3): generate launch campaign, submit
  campaign review, update asset provider notes
- `analytics_provider_reports` (1): run provider report

## Set B — held candidates (28 routes, 10 modules, all adjudicated)

24 canonically added and protected (`TENANT_PROVIDER_MUTATION_ADD`); 1
already-protected exclude (`bookings` — `CUSTOMER_SELF_SERVICE_EXCLUDE`);
3 read-only excludes (`serviceability/check`, `ds` churn/score,
`ds` demand/forecast).

## Mechanism

- 8 services gained a new `_require_trusted_tenant(requested_tenant_id)`
  helper (`ChatService`, `InventoryService`, `AppointmentService`,
  `ServiceCatalogService`, `DispatchService`, `DSService`,
  `SettingsService`, `NotificationService`) — identical shape to the
  pattern established in Slice 2F-35.
- `ChatService` additionally gained `_require_participant` for customer
  principals (no tenant_id to compare).
- `AppointmentService` gained `_assert_appt_access` for the 4
  appointment-object routes with zero tenant/customer parameter.
- 3 inline tenant-ownership checks added: `AppointmentService.
  unblock_calendar_time` (StaffCalendarBlock), `ServiceCatalogService.
  update_item` (ServiceCatalogItem), `DispatchService.reassign_job`
  (DispatchRecord); plus a job.tenant_id cross-check in `dispatch_job`.
- `InventoryService.confirm_reservation`/`release_reservation` gained a
  `StockReservation.tenant_id` WHERE predicate (previously scoped only
  by status).
- `SavedViewService.set_default` hardened with an explicit
  `owner_user_id` re-check (the confirmed partial-ownership gap).
- Router guards swapped `get_current_user`/`require_technician`/bare
  `require_permission` → `require_mutation_access_scope` /
  `require_staff_or_above_mutation` / `require_tenant_mutation_permission`
  per each route's existing role shape — no admitted role narrowed, no
  new guard function added.

## Coverage arithmetic

`c=18, a=24, h=24, r=28` → protected 252+18+24=294, denominator
273+24=297, unprotected 297-294=3, pending held 45-28=17 — exactly
matching the mission's stated expected position for full closure.

## Final status

**CRITICAL_AUTHORIZATION_BATCH_COMPLETE** (per the same 6-status list as
2F-35) — see `approval-gate.md`.
