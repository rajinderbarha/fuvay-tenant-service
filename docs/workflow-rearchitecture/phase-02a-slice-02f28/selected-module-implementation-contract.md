# Selected Module Implementation Contract - Slice 2F-28
## (to be executed by a FUTURE slice; not executed here)

## Selected module
`M01_identity_credentials` - `app.engines.auth.router` / `AuthService`.

## Exact canonical routes (Set A - all 12 MUST be remediated)

1. `DELETE /v1/auth/api-keys/{key_id}`
2. `PATCH /v1/auth/api-keys/{key_id}`
3. `POST /v1/auth/api-keys`
4. `POST /v1/auth/change-password-required`
5. `POST /v1/auth/impersonate`
6. `POST /v1/auth/mfa/confirm`
7. `POST /v1/auth/mfa/disable`
8. `POST /v1/auth/staff/invite`
9. `POST /v1/auth/staff/{user_id}/deactivate`
10. `PUT /v1/auth/me`
11. `PUT /v1/auth/password/change`
12. `PUT /v1/auth/staff/{user_id}/permissions`

## Exact held adjudication routes (Set B)
**None.** No held candidate sits on this boundary (proof in
`selected-held-adjudication-scope.csv`).

## Exact adjacent exclusions (Set C - MUST NOT be touched)
EXCLUDED: `/v1/security/api-keys/{key_id}/rotate`,
`/v1/security/api-keys/{key_id}/revoke`,
`/v1/security/sessions/{session_id}/revoke` (different subsystem/module);
`/v1/auth/mfa/setup`, `/v1/auth/logout`, `/v1/auth/sessions/{session_id}`
(already protected - must not be re-opened);
`/v1/auth/staff/{user_id}/schedule`, `/v1/auth/staff/{user_id}/invite/resend`
(held, not canonical).

## Required authorization pattern
- Self-scoped credential routes: keep authenticated-only admission, but add
  current-credential proof and session invalidation; no tenant authority.
- Staff/API-key/impersonation routes: existing permission **plus**
  mutation-capable access-scope enforcement **plus** object/parent tenant
  ownership proof against the principal's tenant. No new permission or role.

## Required service-layer changes
Enforcement must live in `AuthService`, not only in the router, so a direct
service call cannot bypass it. Alternate staff-deactivate route in
`tenant_engine.portal_router` must receive the same policy.

## Required audits
Read-privacy (404 vs 403 for foreign objects), state-integrity (no
double-revoke / double-deactivate), internal-caller preservation.

## Allowed application files
`app/engines/auth/router.py`, `app/engines/auth/service.py`, and — only for the
alternate-route closure — `app/engines/tenant_engine/portal_router.py`.

## Forbidden application files
Everything else, including `app/core/permissions.py` (no new permission),
`app/dependencies/auth.py` (no new role), any migration, any frontend/mobile
file, and every closed module.

## Expected coverage arithmetic rules
Protected 214 -> up to 226 as routes are closed; denominator stays 259 unless a
held route is added with full evidence. Unprotected 45 -> 33 on full closure.
Report honestly if fewer close.

## Allowed final statuses
`SECURITY_CLOSED`, `SECURITY_CLOSED_PRODUCT_POLICY_BLOCKED`,
`MODULE_IMPLEMENTATION_BLOCKED`, `INCOMPLETE`.

## Stop condition
Stop at that slice's approval gate. Do not select the following module.
