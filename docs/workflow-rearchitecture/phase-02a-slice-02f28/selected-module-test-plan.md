# Selected Module Test Plan - Slice 2F-28 (for the future implementation slice)

Applies to each of the 12 M01 routes unless marked self-scoped.

## Universal matrix

| Case | Expectation |
|---|---|
| Allowed canonical role | 2xx |
| Disallowed role (e.g. customer, technician) | 403 |
| StaffPermission grant for the exact permission | 2xx |
| StaffPermission explicit deny | 403 (deny beats grant) |
| Cross-tenant StaffPermission grant | 403 |
| Read-only mutation access scope | 403 before any body parsing |
| Same-tenant owned object | 2xx |
| Foreign-tenant object | 404 (no existence oracle), never 403-with-detail |
| Missing object | 404 |
| Client-asserted tenant mismatch | 403/404, never honoured |
| Actor/subject mismatch (actor != path target) | authorization decided by target, not actor |
| Invalid state transition (already revoked / already deactivated) | 409 |
| Alternate-route bypass (tenant_engine.portal_router staff deactivate) | same policy |
| Direct service-layer call | service enforces, not only the router |
| Internal/system caller | still works |
| Transaction rollback on guard failure | no partial persistence |
| Audit assertions | actor, target, timestamp recorded |
| Unknown role / unknown scope | fail closed |

## Module-specific cases

- **API keys**: raw key returned exactly once; revoke is idempotent; a revoked
  key cannot authenticate; concurrent revoke does not double-apply.
- **Impersonation**: bounded scope + expiry; impersonated session cannot
  re-impersonate; audit records both real and assumed identity.
- **Password / MFA**: current password or TOTP required; sessions invalidated
  on password change; MFA disable requires a current factor.
- **Staff permissions**: a principal cannot escalate its own permissions; a
  principal cannot grant a permission it does not itself hold.
- **Staff deactivate**: sessions revoked; cannot deactivate the last owner.
