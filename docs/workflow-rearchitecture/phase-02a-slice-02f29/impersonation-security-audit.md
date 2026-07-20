# Impersonation Security Audit - Slice 2F-29

Route: `POST /v1/auth/impersonate`. Final status: `PLATFORM_ADMIN_ONLY`.

## Authority

- Route guard: `require_permission(P.PLATFORM_IMPERSONATE)`.
- Service guard: `AuthService.impersonate` independently requires
  `impersonator.role == "super_admin"`, raising `PermissionDeniedException`
  otherwise. This is the binding constraint and it closes the direct
  service-call path as well as the route.
- **This answers the 2F-28 product question**: effective policy is
  `super_admin` only. `admin_security` is not admitted, because the service
  check rejects it even if the permission were granted. No policy was invented;
  the existing code already decides this.

## Actor / subject separation

- Actor is `uuid.UUID(user.user_id)` from the token; the body cannot supply an
  impersonator.
- Target is resolved server-side by id; `target_role`, `tenant_id` and
  `target_email` in the issued token come from the **target record**, not from
  request fields, so a caller cannot choose an arbitrary role or tenant.
- Inactive target -> `CONFLICT`. Missing target -> `NotFound`.
- Both identities are recorded: audit plus a Redis entry keyed by the
  impersonation session holding `impersonator:target:reason`.
- Token lifetime (60 min) and claims were left exactly as they were - no
  expansion of impersonation capability.

## Not changed

Termination/revocation behaviour was audited but not modified; no new
capability was added.
