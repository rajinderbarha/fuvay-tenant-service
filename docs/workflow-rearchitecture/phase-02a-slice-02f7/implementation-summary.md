# Slice 2F-7 Implementation Summary

## Scope
Fully investigate, classify, protect, and verify every mounted mutation
endpoint owned by `app.engines.serviceability.router` — 19 mounted
mutations, confirmed via runtime introspection (matches the router's own
`endpoint_count: 22` metadata field, which additionally counts 3
non-mutation GET routes not in scope for this workstream).

## What changed

### 1. Backend (`app/engines/serviceability/router.py`)
8 tenant-facing mutations (`create_tenant_service_area`,
`validate_tenant_service_area`, `update_tenant_service_area`,
`delete_tenant_service_area`, `set_primary_tenant_service_area`,
`add_service_mapping`, `update_service_mapping`,
`delete_service_mapping`) previously used plain
`require_permission(P.TENANT_SERVICE_AREA_*)` with **no access-scope
check at all** — a read-only-scoped tenant_owner
(`access_scope="customer_support_limited"`) could mutate service-area
coverage despite holding the permission bundle. Fixed by wrapping all 8
in `require_tenant_mutation_permission(...)`, the same composed guard
used for `tenant_engine.router` (Slice 2F-1), `admin_catalog.tenant_router`,
and `invoice_payment.provider_issue_invoice` (Slice 2F-6). No new
permission was created; the guard reuses the existing dependency.

Persona evidence (re-verified, not assumed): `TENANT_SERVICE_AREA_CREATE/
UPDATE/DELETE/SERVICE_CREATE/SERVICE_UPDATE/SERVICE_DELETE` are granted
**only to `tenant_owner`** in `ROLE_PERMISSIONS` — `staff`/`technician`
hold only the `READ` permission ("view not edit," per the `staff`
bundle's own comment). So technician was already denied at the
permission level before this slice (no new denial needed); the fix
closes the access-scope gap for the one role (`tenant_owner`) that does
hold these permissions.

The 4 platform-admin routes (`admin_create_service_area`,
`admin_update_service_area`, `admin_delete_service_area`,
`admin_serviceability_test`) and the 3 query/check routes
(`check_serviceability`, `matching_tenants`, `available_services`) and 4
customer-address routes were confirmed to require no change — added to
the inventory tool's allowlists with documented evidence instead.

### 2. Tooling (`scripts/workflow_rearchitecture/inventory_mutation_routes.py`)
`CONFIRMED_FALSE_POSITIVE_ROUTES` extended with the 4 customer-address
routes and 3 query routes; `CONFIRMED_PLATFORM_ADMIN_PERMISSION_ROUTES`
extended with the 4 admin routes — bringing `--verify-module` to 0
unverified for `serviceability.router` (19/19).

### 3. Frontend (`app/(tenant)/provider/service-areas/page.tsx`)
Found (via direct investigation, not assumed): this page's
`canCreate`/`canUpdate`/`canDelete`/`canSetPrimary` booleans were
hardcoded to `true` for any authenticated tenant user, with a code
comment acknowledging the gap explicitly. Fixed by computing them from
the existing `getUserRole()`/`isTenantOwnerRole()`/`isTenantReadOnly()`
helpers, matching the actual backend policy (tenant_owner only,
mutation-capable scope required). No new frontend authorization system,
no visual redesign — only the boolean computation changed.

### 4. Test suite
New: `tests/test_phase2f7_serviceability_authorization.py` (80 tests —
persona enforcement for all 8 tenant routes + 4 platform-admin routes,
direct cross-tenant rejection via genuine service-layer fixtures,
duplicate/advisory-lock guard regression, module-verification parity).
Updated (documented growth, not weakened): `test_phase2d_tenant_access_model.py`
and `test_tenant_service_coverage_enterprise_ui.py`'s "living count"
guardrail tests, which correctly flagged that a 5th file now uses
`require_tenant_mutation_permission`.

## What did NOT change
No previously-closed module was modified. Invoice/payment closure (Slice
2F-6/2F-6A/2F-6B) was not reopened. `admin_catalog.tenant_router` and
`complaints.provider_router` were not begun. No permission was granted.
No new role was introduced. `readonly@` and migration 144 were untouched.

## Key findings documented but not fixed
- No canonical geography reference table exists platform-wide (a
  significant, pre-existing platform characteristic, not invented or
  fixed here).
- No tenant-catalog-enablement check on service mappings (owned by
  `admin_catalog`, out of scope).
- No audit event for service-mapping mutations (design-choice, not
  mechanical).
- A separate, unrelated `geo`-module zone-management page exists in the
  same frontend area — not touched (different backend module).

## Outcome
`SECURITY_AND_DOMAIN_INTEGRITY_CLOSED_PRODUCT_POLICY_BLOCKED` — see
`approval-gate.md`. Global tenant-mutation coverage moves from 89/183 to
**97/183**.
