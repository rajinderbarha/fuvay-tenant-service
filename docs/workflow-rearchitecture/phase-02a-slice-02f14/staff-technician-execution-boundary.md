# Staff/Technician Execution Boundary

## New named dependency

`require_staff_or_technician_only` (`app/dependencies/auth.py`) — admits only `role in
("staff", "technician")`. Deliberately narrower than the pre-existing `require_technician`
(which also admits `tenant_owner`/`super_admin`): this is a staff/technician *self-service
execution* capability, not a tenant-oversight one (tenant_owner already has its own tenant-scoped
routes for the equivalent oversight actions, gated separately by
`require_tenant_mutation_permission`).

## Applied to

- All 6 `field_ops.staff_router` routes (via the shared `_svc` factory).
- 7 `field_ops.router` routes: `accept_job`, `reject_assignment`, `start_checklist`,
  `update_checklist_item`, `complete_checklist`, `submit_findings`, legacy `update_checklist`.

## Verified exclusion

`TestFieldOpsRouterAlternateRouteGate::test_tenant_owner_denied_from_execution_alternates`
confirms a `tenant_owner` account is correctly rejected (403) from these 7 execution-only
routes — tenant oversight of jobs still happens through `assign_job`/`update_status` (which
remain accessible to `tenant_owner` via `require_tenant_mutation_permission`), not through the
technician-personal execution actions.

## Role-naming correction (pre-existing, re-verified not re-broken)

The real seeded role is `"technician"`, not `"staff"` (see
`test_p0_job_completion_credit_deduction.py`'s history). `require_staff_or_technician_only`
correctly admits both.
