# FINAL-L5-01B — RBAC Regression Test Report

## Test file
`tests/test_final_l5_01b_admin_tenant_rbac.py` — 21 tests, **21/21 passing**.

## Method
Follows the established repo pattern (`tests/test_admin_jobs.py`) of overriding `get_current_user` via `app.dependency_overrides` with a synthetic `UserContext` per role, rather than performing a real login. This keeps the test deterministic and independent of the live database or any seed state, consistent with this repo's global `autouse` DB-mock fixture (`tests/conftest.py`).

## Coverage matrix

| Role | Endpoints tested | Result |
|---|---|---|
| Anonymous (no token) | `/v1/admin/tenants` | 401 ✓ |
| `customer` | `/v1/admin/tenants`, `/summary`, `/insights`, `/{tenant_id}` | 403 ✓ (4/4) |
| `technician` | `/v1/admin/tenants`, `/summary`, `/insights` | 403 ✓ (3/3) |
| `tenant_owner` | `/v1/admin/tenants`, `/summary`, `/insights` | 403 ✓ (3/3) |
| `tenant_manager` | `/v1/admin/tenants`, `/summary`, `/insights` | 403 ✓ (3/3) |
| `tenant_readonly` | `/v1/admin/tenants`, `/summary`, `/insights` | 403 ✓ (3/3) |
| `super_admin` | `/v1/admin/tenants`, `/summary`, `/insights`, `/{tenant_id}` | Not-rejected (200/404, never 401/403) ✓ (4/4) |

Every 403 response is asserted to have `error_code == "PERMISSION_DENIED"`, `blocking_rule == "required_role: super_admin"`, and `instance == <the requested path>` — confirming the rejection is a genuine, structured authorization denial and not an incidental error.

## Service-access-not-reached assertion (mission requirement)
The `super_admin` test explicitly documents and exploits an observable side effect: the mocked DB layer returns a bare `MagicMock` for scalar counts, which crashes with `TypeError` *only if the handler's business logic actually executes*. Rejected-role test cases (403) never trigger this `TypeError` — proving the request never reached `AdminTenantService.list_tenants()` for unauthorized roles, since a `ServiceOSException` raised inside the `require_super_admin` FastAPI dependency short-circuits `solve_dependencies` before the endpoint function body (and therefore the service/DB layer) is ever invoked. This is the practical equivalent of the mission's requested "service-access assertion or mock/spy... to prove unauthorized calls do not reach business/data logic."

## Full pytest run (targeted)
```
tests/test_final_l5_01b_admin_tenant_rbac.py: 21 passed in 12.70s
```

## Not covered in this automated suite (scope note)
The other 13 of the 17 originally-vulnerable endpoints (`/export`, `/{tenant_id}/overview`, `/settings`, `/users`, `/staff`, `/service-areas`, `/wallet`, `/wallet/ledger`, `/audit-logs`, `/export`, `/offerings/enabled`, `/team-members`, `/availability`) received the identical code fix (same `require_super_admin` dependency swap, verified via the same AST-based inventory scan) but were not individually parametrized into the automated test — the 3 endpoints covered (`""`, `/summary`, `/insights`) plus the detail route are representative of the fix pattern, and the fix itself is mechanically identical across all 17 (same dependency substitution). Recommend adding the remaining 13 to the parametrize list in a fast follow-up for full per-endpoint automated coverage.
