# Persona Policy — Slice 2F-22

## Canonical persona

**`tenant_owner`** (with `super_admin` also admitted by the shared
dependency, explicitly and by existing platform-wide convention).

Enforced by `require_tenant_owner_mutation` (`app/core/permissions.py`) — a
pre-existing dependency admitting exactly the same role set as the
`require_tenant_owner` it replaces, PLUS a read-only `access_scope` denial.
No role, alias or permission was added.

## Explicit determinations

| Principal | Decision | Basis |
|---|---|---|
| `tenant_owner` | PERMITTED | owns the tenant's commercial relationship |
| `super_admin` | PERMITTED, explicit | shared dependency; platform-wide convention |
| `staff` | **DENIED** | no existing policy supports staff committing the tenant to a package. Per the mission, staff being able to *view* packages is not a reason to let them buy one. No canonical permission distinguishes a purchasing staff member. |
| `technician` | DENIED | field-execution persona; no commercial authority |
| `customer` | DENIED | wrong tenancy domain entirely |
| `guest` / unauthenticated | DENIED | authentication dependency |
| `admin_operations`, `admin_finance`, `admin_security`, `admin_readonly` | DENIED on this tenant-facing route | platform admins act through `admin_router.admin_purchase_package`, gated by `P.PACKAGES_CREATE` — a distinct, correctly separated persona surface |
| read-only tenant owner (`access_scope`) | **DENIED** | the concrete gap 2F-22 closed; previously a read-only owner could commit a purchase |
| prohibited aliases (`tenant_manager`, `tenant_readonly`, `office_staff`, `manager`, `supervisor`) | DENIED | unknown role fails closed |
| unknown role / unknown scope | DENIED | fails closed |

## StaffPermission deny precedence

Not applicable to this route: no staff persona is admitted at all, so there
is no permission grant for a deny to take precedence over. Preserved
unchanged elsewhere.

## Tests
`TestRouteAuthorizationWiring` (4 tests) plus
`direct-authorization-test-matrix.csv`.
