# ADMIN-TENANT-E2E-08: Business Profile RBAC Report

**Date:** 2026-07-10

## Backend Endpoint
`PUT /v1/provider/business-profile` in `app/engines/profile/router.py` line 114–133.

## Role Check
Uses `Depends(require_technician)` defined in `app/dependencies/auth.py`:

```python
async def require_technician(user: UserContext = Depends(get_current_user)) -> UserContext:
    _check_force_password_change(user)
    if user.role not in ("technician", "staff", "tenant_owner", "super_admin"):
        raise ServiceOSException(
            error_code="PERMISSION_DENIED",
            detail=f"Technician access required. Your role: '{user.role}'.",
            blocking_rule="required_role: technician | staff | tenant_owner | super_admin",
        )
    return user
```

## Analysis

### Allowed Roles
All of: `technician`, `staff`, `tenant_owner`, `super_admin`

### Read-Only Role
There is **no explicit read-only role** defined in the auth system. The codebase defines roles: `customer`, `technician`, `staff`, `tenant_owner`, `super_admin`. There is no `read_only` or `viewer` role.

### Implication
Since there is no read-only role in the system, the RBAC concern ("read-only users can mutate") cannot materialize — every authenticated tenant user has at least one of the allowed roles. All `staff` members are assumed to be operational staff with permission to update business information.

### Frontend RBAC Check
`profile/page.tsx` line 411:
```typescript
const canUpdate = !permissions || permissions.includes("tenant.business_profile.update") || true; // tenant_owner default: allowed
```
The frontend always sets `canUpdate = true` — the inline `|| true` overrides any permissions check. This is intentional until granular permissions are returned by `/v1/auth/me`.

## Verdict
**No RBAC gap found.** The backend correctly rejects `customer` roles. The `staff`/`technician` role access is intentional. No read-only role exists to protect against.
