# Affected Account — Final Disposition

## manager@demo-ac-services.local

| Field | Value |
|---|---|
| Current state (before this slice) | `role='tenant_manager'`, `is_active=true`, 0 logins, 0 sessions |
| Disposition | `DISABLE_DEMO_ACCOUNT` |
| Proposed state | `role='staff'` (required canonical placeholder — the constraint needs *some* valid value; this is not a capability grant), `is_active=false`, `deactivated_at`/`deactivation_reason` recorded |
| Evidence | Zero logins, zero sessions, zero audit records of any kind since creation on 2026-07-11 — no active use to protect. Manager-persona permissions cannot be safely granted regardless (see `manager-persona-decision.md`), so even an "active" version of this account couldn't do what its name implies today. |
| Access differences | Before: nominally "tenant_manager" but actually zero effective permissions (unrecognized role). After: `staff` role but `is_active=false`, so also zero effective access (login itself is blocked). Net access change: none in practice (it went from accidentally-zero to deliberately-zero), but now in a canonical, constraint-compliant, clearly-documented state. |
| Risk | Minimal — no user was relying on this account |
| User impact | None detected — zero historical usage |
| Session action | 0 sessions existed; 0 revoked (nothing to revoke) |
| Notification action | None sent — no evidence of a real owner to notify, and the account was never functional to begin with |
| Rollback plan | `UPDATE users SET role='tenant_manager', is_active=true, deactivated_at=NULL, deactivation_reason=NULL WHERE id='72640932-ef3c-4ce5-92a1-6609bff35ee0'` would restore the exact prior state (previous role value preserved in the `auth_audit_logs` metadata for this purpose) — though rolling back to an invalid role is not recommended; if reactivation is ever needed, do so with a proven role/permission configuration instead |

**Status: EXECUTED this slice.** Verified live: role distribution shows zero `tenant_manager` rows; `auth_audit_logs` contains one `role.remediation` event with full before/after metadata.

## readonly@demo-ac-services.local

| Field | Value |
|---|---|
| Current state | `role='tenant_readonly'`, `is_active=true`, 7 logins, 7 unrevoked sessions |
| Disposition | `MANUAL_CONFIRMATION_REQUIRED` (equivalently `RETAIN_BLOCKED_PENDING_PRODUCT_DECISION`) |
| Proposed state | No change proposed this slice |
| Evidence | 7 real logins across 3 days prove active, repeated interest in using this account — but zero non-login audit actions were ever recorded (consistent with the account being unable to do anything, since its role grants zero permissions). This is real usage that must not be silently disabled per the brief's explicit instruction. |
| Access differences if remediated to `staff` | Would go from zero effective permissions to the FULL base `staff` bundle (own-job read/update/close, quote management, parts, chat) — this is a significant *increase* in mutation capability, not a lateral "read only" move, and would violate rule 3 ("do not map tenant_readonly to staff unless the permission system can enforce genuinely read-only access" — which Workstream 3 proved it cannot, comprehensively, today) |
| Risk of mapping to `staff` today | High — would grant real mutation capability to an account explicitly intended (per its name and demo-tenant context) to be restricted, with no enforced restriction actually in place |
| Risk of leaving unchanged | Low-to-moderate — account remains functionally inert (zero permissions), so no unauthorized action is possible; the only cost is the account owner's continued frustration at an account that doesn't work, and this account continuing to block migration 144 |
| User impact if unchanged | Whoever has been logging in 7 times continues to be unable to do anything with this account |
| Session action | None taken — sessions remain unrevoked since no role change occurred; revoking sessions without a replacement role would just add "can't even log in" to "can't do anything once logged in," which isn't clearly better |
| Notification action | None sent |
| Rollback plan | N/A — no change was made |

**Status: NOT remediated. Genuinely blocked** on a product decision: (a) accept `staff` mapping despite the capability increase, accepting the risk described above, (b) invest in closing the read-only enforcement coverage gap (`tenant-readonly-decision.md`) first, then map to `staff` with `access_scope` restriction once that's comprehensive, or (c) deactivate the account and have its real user (if one exists beyond the demo environment) go through a proper access request.

## Migration 144 impact
Because `readonly@demo-ac-services.local` remains invalid, migration 144 correctly still refuses to apply — confirmed live this slice (`alembic upgrade head` aborts naming only this one account; database remains at revision 143).
