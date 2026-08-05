import { SecurityCapabilities } from "./customerSecurity";

/**
 * Derived from confirmed real routes/screens (spec section 3), audited
 * directly against `app/engines/auth/{router,service}.py`:
 * - canChangePassword: `PUT /v1/auth/password/change` -- real, requires
 *   correct current password, now also revokes other sessions on success.
 * - canRequestPasswordReset: `POST /v1/auth/password/reset/request` +
 *   `.../confirm` -- both real; confirm previously stubbed
 *   (`SERVICE_UNAVAILABLE`) and is now implemented for real this phase.
 * - canSetupMfa/canDisableMfa: the full enrollment contract exists
 *   (`/mfa/setup` -> `/mfa/confirm`, TOTP+password-gated `/mfa/disable`).
 * - canListSessions/canRevokeSession: `GET /v1/auth/sessions` +
 *   `DELETE /v1/auth/sessions/{id}` -- real, customer-scoped.
 * - canManageSessions: true as of the Manage Sessions phase -- the real
 *   screen now exists (`ManageSessionsScreen`), backed by the same
 *   `GET /v1/auth/sessions` / `DELETE /v1/auth/sessions/{id}` routes.
 * - canRevokeOtherSessions: `POST /v1/auth/sessions/revoke-all-other` --
 *   real; fixed this phase to genuinely exclude the caller's own session
 *   (previously revoked everything despite its docstring's promise).
 * - canGlobalLogout: `POST /v1/auth/logout-all` -- real, revokes every
 *   session including the current one.
 */
export function resolveSecurityCapabilities(): SecurityCapabilities {
  return {
    canChangePassword: true,
    canRequestPasswordReset: true,
    canSetupMfa: true,
    canDisableMfa: true,
    canListSessions: true,
    canRevokeSession: true,
    canManageSessions: true,
    canRevokeOtherSessions: true,
    canGlobalLogout: true,
  };
}
