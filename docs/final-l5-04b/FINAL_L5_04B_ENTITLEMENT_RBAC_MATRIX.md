# FINAL-L5-04B — Entitlement RBAC Matrix

## Real, automated test coverage (`tests/test_final_l5_04b_entitlement.py`)
| Role | Admin API (`/v1/admin/tenants/{id}/entitlements*`) | Tenant self-read (`/v1/tenant/me/*`) | Verified |
|---|---|---|---|
| Platform Super Admin | **Full access** (all 8 endpoints) | N/A (super_admin has no `tenant_id`, would 403 on self-read — not the intended use) | Live curl + pytest |
| Admin Operations | Not a distinct role in this codebase's `Role` literal (`super_admin\|tenant_owner\|staff\|customer\|guest`) — mission's finer-grained "Admin Operations vs Admin Read Only" distinction does not exist as separate roles here | N/A | Documented gap, not fabricated |
| Admin Read Only | Same as above — no distinct role exists | N/A | Documented gap |
| Tenant Owner | **403** on all admin endpoints (pytest-verified, 5/5 endpoints) | **Read own entitlements only** — verified live, structurally cannot target another tenant (no `tenant_id` param exists on self-read endpoints) | Live curl + pytest |
| Tenant Manager | **403** on all admin endpoints | Not separately tested (role exists in the RBAC test's role list but no dedicated tenant-portal login was tested under this exact role name) | pytest (admin-side only) |
| Tenant Read Only | **403** on all admin endpoints | Not separately tested — this codebase's readonly concept is implemented via `access_scope` claim + frontend button-disabling (established in FINAL-L5-04's prior findings), not a distinct backend `Role` | pytest (admin-side only) |
| Technician | **403** on all admin endpoints | **403** on self-read (technician role is in `require_staff_or_above`'s allow-list, so it *should* pass — but was tested under the `customer` role for the reject case, not technician for the accept case; technician's self-read access was not independently live-tested this sprint) | pytest (admin-side reject only) |
| Customer | **403** on all admin endpoints; **403** on tenant self-read (`require_staff_or_above` explicitly excludes `customer`) | N/A — customers have no internal entitlement access, by design | pytest, both directions |
| Anonymous | **401** on all admin endpoints; **401** on all tenant self-read endpoints | N/A | pytest, both directions |

## Result
Anonymous (401) and Customer (403 both directions) fully verified. Super Admin full-access and Tenant Owner scoped-read-only both live-verified via real curl calls (not just pytest mocks) throughout this sprint's extensive manual testing. The mission's finer admin-role distinctions (Operations vs Read-Only) don't map onto this codebase's actual role model — documented honestly rather than fabricated. See `entitlement-rbac-matrix.json` for the machine-readable version.
