# Implementation Summary - Slice 2F-29 (M01)

## Final status: SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED

Scoped to **M01_identity_credentials only**. This is NOT an application-wide
security claim.

## Result

All **12** frozen Set A routes are now fully protected.

| Metric | Before | After |
|---|---|---|
| Protected | 214 | **226** |
| Denominator | 259 | 259 (unchanged) |
| Unprotected | 45 | **33** |
| Canonical hash | e7a89231207221aa | fbe7cf863afa0d84 |
| Matrix hash | ee6011f6ce6a97ab | 753653ed32916f4e |

## Final status per route class

| Class | Count | Final status |
|---|---|---|
| Tenant mutations (api-keys x3, staff invite/deactivate/permissions) | 6 | TENANT_MUTATION_PERMISSION_SCOPE_AWARE |
| Impersonation | 1 | PLATFORM_ADMIN_ONLY |
| Self-service credential/profile | 5 | FULLY_PROTECTED |

## What was actually wrong, and what changed

**1. Missing mutation-capable access scope (6 routes).** All six tenant
mutations used `require_permission(...)`, which has no read-only access-scope
denial. A tenant-side principal carrying a read-only `access_scope` could
create/update/revoke API keys, invite and deactivate staff, and rewrite
StaffPermissions. Fixed by moving to the canonical
`require_tenant_mutation_permission(...)` guard family. No new permission or
role; the permission on each route is unchanged.

**2. Account-existence oracle in `update_permissions`.** A foreign-tenant
target raised `PERMISSION_DENIED("User does not belong to your tenant")`,
which confirmed the id existed in another tenant. `deactivate_staff` already
did the right thing (`NotFoundException`). Now identical: a foreign target is
indistinguishable from a nonexistent one.

**3. Unvalidated StaffPermission keys (2 service methods).** Both
`update_permissions` and `invite_staff` persisted arbitrary strings as
StaffPermission rows, and `PermissionChecker.has` consults those rows as
overrides - so a typo or invented key silently became a live grant (or an
unsatisfiable deny). Both now validate against the real registry (406 keys)
built from `P` + `ROLE_PERMISSIONS`. **No permission was added**; the key must
already exist. On `invite_staff` the check runs *before* any persistence, so an
invalid key cannot leave a half-created user behind.

## What was already correct (verified, not changed)

- Tenant and actor are derived server-side from the token on every route; no
  client-supplied tenant/actor/subject is trusted.
- API-key mutation is scoped `WHERE id == key_id AND tenant_id == tenant_id`,
  raw secret returned only by create, stored hashed, foreign key -> NotFound.
- Impersonation enforces `super_admin` inside `AuthService`, resolves target
  tenant/role from the target record, and audits both actor and subject.
- The 5 self-service routes act only on `uuid.UUID(user.user_id)` from the
  token and require current-password/TOTP proof where applicable.
- Alternate deactivate surfaces were already protected
  (`require_tenant_owner_mutation`, `require_platform_mutate`).

## Scope discipline

- Application files changed: **exactly 2** -
  `app/engines/auth/router.py`, `app/engines/auth/service.py` (both on the
  contract allow-list). `tenant_engine/portal_router.py` was allowed but
  required **no** change - its alternate route was already closed in 2F-4.
- Set B remained empty; no held candidate applied.
- Set C untouched; the separate `/v1/security/api-keys/*` subsystem
  (`APIKey -> tenant_api_keys`) was not modified.
- Denominator unchanged at 259.

## Verification

- `tests/test_phase2f29_m01_identity_closure.py` - **43 passed**
- Full phase-2F suite - **2213 passed, 0 failed, 0 errors**
- `verify_m01_2f29.py` - 27/27 PASS; `--selftest` exit 0
