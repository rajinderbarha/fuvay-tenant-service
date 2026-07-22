# Global Coverage Update — Workstream 16

## Reconciliation method
Re-ran the runtime mutation inventory tool with no module filter, then
filtered to `TENANT_USER_MUTATION` + `TENANT_TECHNICIAN_MUTATION`
auto-classified routes (the established denominator convention from
Slice 2F/2F-6/2F-6A), and to the file's own "fully_protected" counting
convention (scope/role-aware guard only, excluding `PLATFORM_ADMIN_ONLY`
routes from the numerator).

## Corrected totals

| Metric | Previous (Slice 2F-6) | After this slice |
|---|---|---|
| Total tenant-facing mutations | 183 | **183** (unchanged — confirmed via runtime re-verification; the 8 `serviceability.router` tenant routes were already counted in this denominator, not newly discovered) |
| Protected tenant-facing mutations | 89 | **97** (+8) |
| Remaining unprotected | 94 | **86** |

## Routes newly protected (8)
`create_tenant_service_area`, `validate_tenant_service_area`,
`update_tenant_service_area`, `delete_tenant_service_area`,
`set_primary_tenant_service_area`, `add_service_mapping`,
`update_service_mapping`, `delete_service_mapping` — all moved from
`PERMISSION_ONLY_NOT_SCOPE_AWARE` to `TENANT_MUTATION_PERMISSION_SCOPE_AWARE`
via `require_tenant_mutation_permission(...)`.

## Platform-only routes excluded (re-confirmed, not recombined into the denominator)
`admin_create_service_area`, `admin_update_service_area`,
`admin_delete_service_area`, `admin_serviceability_test` — gated by
`PLATFORM_ADMIN`/`SERVICEABILITY_ADMIN_TEST`, granted to no role but
`super_admin`. Also excluded (not tenant-facing at all):
`create_my_address`, `update_my_address`, `delete_my_address`,
`set_default_address` (customer-only), `check_serviceability`,
`matching_tenants`, `available_services` (query capabilities, 2 of the 3
perform no DB write at all).

## Routes reclassified
None reclassified from tenant-facing to platform-only or vice versa —
the 8/19 split was already correct from the runtime auto-classification;
this slice only changed the *guard*, not the *classification*, of the 8
tenant routes.

## Remaining module count
17 tenant-facing modules remain with at least one unprotected mutation
(down from 18 before this slice) — `serviceability.router` is now fully
closed.

## Remaining unverified count
0 within `serviceability.router` (re-verified: `total_routes: 19`,
`unverified_count: 0`, exit 0). Platform-wide unverified count not
recomputed in full this slice (Slice 2F-6's own report already
established the platform-wide `UNVERIFIED` bucket spans many
out-of-scope modules).

## Files updated
- `docs/workflow-rearchitecture/phase-02a-slice-02f/tenant-mutation-endpoint-inventory.csv`:
  updated in place — the 8 serviceability rows' `guard_status`,
  `required_change`, and `verification_level` columns corrected to
  reflect the fix.
- `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`:
  updated in place — `serviceability.router`'s row and the running TOTAL
  row (89 → 97, 48.6% → 53.0%).
