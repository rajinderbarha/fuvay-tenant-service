# ADMIN-TENANT-E2E-10 — Job RBAC Report

## Static Analysis Only

## Frontend RBAC

### Auth Token Handling
- All job API calls use `apiFetch()` from `lib/api.ts`
- `apiFetch` attaches the auth token from cookie/storage automatically
- No RBAC role checks in the tenant portal frontend itself

### Tenant Isolation
- Job list: `GET /v1/jobs` — backend scopes to authenticated tenant
- Job detail: `GET /v1/jobs/{id}` — backend validates tenant ownership
- Assignment API: `GET/POST /v1/provider/service-jobs/{id}/*` — tenant-scoped

### Read-Only Role Concern (Tenant Users)
- The tenant portal does not implement role-based button hiding for read-only users
- If a tenant has read-only users, they can access all action buttons in the UI
- Backend must enforce role restrictions on mutation endpoints
- Frontend provides no additional guard

### Backend RBAC Assessment (Static — Backend Directory Inaccessible)
The backend source was not accessible at `g:\serviceos\backend` during this run. RBAC enforcement could not be directly verified from backend source code.

Based on Sprint 31 memory notes:
- `TenantScopeService` + `require_customer`/`require_technician` patterns were implemented
- Invoice/job tenant-scope fixes were applied in Sprint 31
- Job mutation endpoints are expected to check tenant_id scope

### Mutation Actions in Tenant Jobs UI
| Action | Endpoint | Mutation |
|--------|----------|----------|
| Status update | `PUT /v1/jobs/{id}/status` | Write |
| Close job | `POST /v1/jobs/{id}/close` | Write |
| Send quote | `POST /v1/jobs/{id}/quote` | Write |
| Update checklist | `PUT /v1/jobs/{id}/checklist` | Write |
| Submit findings | `POST /v1/jobs/{id}/findings` | Write |
| Spawn repair | `POST /v1/jobs/{id}/spawn-repair` | Write |
| Assign technician | `POST /v1/provider/service-jobs/{id}/assign` | Write |
| Schedule | `POST /v1/provider/service-jobs/{id}/schedule` | Write |
| Cancel assignment | `POST /v1/provider/service-jobs/{id}/cancel-assignment` | Write |
| Approve parts | `POST /v1/provider/service-jobs/{id}/parts/{pr_id}/approve` | Write |

## Findings
- Backend tenant-scope enforcement: ASSUMED PRESENT (Sprint 31)
- Frontend read-only role guard: NOT IMPLEMENTED — all buttons visible to all tenant users
- No IDOR risk at frontend (IDs always come from authenticated session data)

## Recommendation
If tenant user roles (admin/staff/viewer) are implemented, add role check before rendering action buttons. Currently this is a backend-only concern.

## Status: PARTIAL — Backend RBAC assumed; frontend has no role-based button suppression
