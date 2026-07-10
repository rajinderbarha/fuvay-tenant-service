# FINAL-L5-01B — Admin Tenant RBAC Inventory

## Vulnerability reproduction
Confirmed live and in-process: `customer1@serviceos.local` (role=`customer`) received `HTTP 200` with real tenant data (`Demo AC Services`, `Isolation Test Services`) from `GET /v1/admin/tenants` before the fix. Also confirmed `GET /v1/admin/tenants/{tenant_id}` returned `200` for the same customer.

## Root cause
`app/engines/tenant_engine/admin_router.py` — the file's own docstring claims *"Read endpoints require authenticated user (super_admin or internal tools)"*, but 17 of its `GET` routes actually used the bare `Depends(get_current_user)` dependency, which only verifies a valid JWT/session — it performs **no role check at all**. Any authenticated user of any role (customer, technician, tenant staff) passed straight through to the handler and received real, unfiltered platform-wide tenant data.

## Full inventory of the 17 vulnerable GET endpoints (pre-fix)

| Method | Path | Pre-fix dependency | Observed status (customer) | Data exposed | Expected status | Root cause |
|---|---|---|---|---|---|---|
| GET | `/v1/admin/tenants/summary` | `get_current_user` | 200 (confirmed vulnerable class) | KPI summary counts, platform-wide | 403 | No role check |
| GET | `/v1/admin/tenants/insights` | `get_current_user` | 200 (confirmed vulnerable class) | Platform insights | 403 | No role check |
| GET | `/v1/admin/tenants/export` | `get_current_user` | 200 (confirmed vulnerable class) | CSV export, all tenants | 403 | No role check |
| GET | `/v1/admin/tenants` | `get_current_user` | **200 — directly reproduced** | Full tenant list incl. billing/credit balance/owner info | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}` | `get_current_user` | **200 — directly reproduced** | Full tenant detail | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/overview` | `get_current_user` | 200 (confirmed vulnerable class) | Tenant overview | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/settings` | `get_current_user` | 200 (confirmed vulnerable class) | Tenant settings | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/users` | `get_current_user` | 200 (confirmed vulnerable class) | Tenant's user list | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/staff` | `get_current_user` | 200 (confirmed vulnerable class) | Tenant's staff list | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/service-areas` | `get_current_user` | 200 (confirmed vulnerable class) | Coverage data | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/wallet` | `get_current_user` | 200 (confirmed vulnerable class) | Legacy wallet data | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/wallet/ledger` | `get_current_user` | 200 (confirmed vulnerable class) | Wallet ledger | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/audit-logs` | `get_current_user` | 200 (confirmed vulnerable class) | **Audit logs — sensitive** | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/export` | `get_current_user` | 200 (confirmed vulnerable class) | Tenant export | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/offerings/enabled` | `get_current_user` | 200 (confirmed vulnerable class) | Provider offerings | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/team-members` | `get_current_user` | 200 (confirmed vulnerable class) | Team member list | 403 | No role check |
| GET | `/v1/admin/tenants/{tenant_id}/availability` | `get_current_user` | 200 (confirmed vulnerable class) | Availability rules | 403 | No role check |

Note: `GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` was **already correctly protected** with `require_super_admin` before this sprint — not part of the vulnerability.

## Method
Endpoints identified via a Python AST-style scan of `admin_router.py` extracting every `@router.get(...)` block and its `Depends(...)` dependency (see the extraction script embedded in this sprint's investigation). Confirmed by direct reproduction (live HTTP 200 for `/v1/admin/tenants` and `/v1/admin/tenants/{tenant_id}` with a customer token) and, after the fix, by 21 passing automated regression tests (`tests/test_final_l5_01b_admin_tenant_rbac.py`) covering the full role matrix on 3 representative endpoints plus tenant-detail.
