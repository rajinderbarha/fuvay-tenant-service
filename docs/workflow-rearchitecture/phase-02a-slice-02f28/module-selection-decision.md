# Module Selection Decision - Slice 2F-28

## Selected: M01_identity_credentials (`app.engines.auth.router`) - 12 routes

| Route | Endpoint | Current guard | Mutated resource |\n|---|---|---|---|\n| `DELETE /v1/auth/api-keys/{key_id}` | revoke_api_key | PERMISSION_ONLY_NOT_SCOPE_AWARE | ApiKey (api_keys) |
| `PATCH /v1/auth/api-keys/{key_id}` | update_api_key | PERMISSION_ONLY_NOT_SCOPE_AWARE | ApiKey (api_keys) |
| `POST /v1/auth/api-keys` | create_api_key | PERMISSION_ONLY_NOT_SCOPE_AWARE | ApiKey (api_keys) |
| `POST /v1/auth/change-password-required` | change_password_required | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK | User.password_hash |
| `POST /v1/auth/impersonate` | impersonate | PERMISSION_ONLY_NOT_SCOPE_AWARE | Session/token |
| `POST /v1/auth/mfa/confirm` | confirm_mfa | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK | MfaSecret |
| `POST /v1/auth/mfa/disable` | disable_mfa | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK | MfaSecret |
| `POST /v1/auth/staff/invite` | invite_staff | PERMISSION_ONLY_NOT_SCOPE_AWARE | User (staff) |
| `POST /v1/auth/staff/{user_id}/deactivate` | deactivate_staff | PERMISSION_ONLY_NOT_SCOPE_AWARE | User (staff) |
| `PUT /v1/auth/me` | update_profile | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK | User (self profile) |
| `PUT /v1/auth/password/change` | change_password | AUTHENTICATED_ONLY_NO_PERMISSION_CHECK | User.password_hash |
| `PUT /v1/auth/staff/{user_id}/permissions` | update_permissions | PERMISSION_ONLY_NOT_SCOPE_AWARE | StaffPermission |

## Rationale (against the 12 required selection criteria)

1. **Security severity** - highest. Credential, API-key, impersonation and
   permission mutation in one module.
2. **Route count** - largest in the queue (12 of 45 = 27%).
3. **Credential/identity sensitivity** - password change, MFA confirm/disable,
   API-key lifecycle. Compromise here defeats every other control.
4. **Cross-tenant impact** - staff deactivate / permissions / API keys are
   addressed by object id with a permission-only gate and no verified
   object-ownership check.
5. **Destructive/irreversible** - API-key revoke and staff deactivate.
6. **External/financial** - low; not a reason to defer.
7. **Product-policy readiness** - `product_blockers = 0`. Roles and permissions
   already exist (`auth:apikeys:manage`, `auth:staff:invite`,
   `auth:staff:manage`, `auth:permissions:manage`, `platform:impersonate`).
   No new permission is needed.
8. **Atomic closure** - one router, one service (`AuthService`), one coherent
   boundary.
9. **Testability** - scored 3. Deterministic HTTP-level tests; no async worker
   or external gateway in the path.
10. **Held-candidate uncertainty** - **zero** held candidates on this boundary
    (verified). Nothing must be adjudicated before closure.
11. **Dependencies** - none on unfinished modules.
12. **Risk reduction per slice** - highest (priority 35 vs 21 next).

## Why the next-ranked modules were NOT selected

- **M02_media_assets (21)** - 9 routes, real cross-tenant delete exposure, but
  lower severity (no credential/permission authority) and it carries
  `product_blockers=1` plus 3 same-module held candidates (`/v1/media/*`)
  needing adjudication first. Better sequenced after M01.
- **M06_security_deposit (20)** - highest financial risk and a genuine
  client-asserted-tenant defect, but only 3 routes and `product_blockers=2`
  (deposit lifecycle policy is undecided; two of its routes are mutating GETs
  whose lazy-create behaviour is itself a product question). Not ready.
- **M10 / M11 (14 / 12)** - genuinely severe per-route (geo zone deletes with
  no tenant predicate at all) but 1 route each; low leverage. They are strong
  candidates for a combined follow-up slice.
- **M03 (14)** - 6 routes but self-scoped grid personalization; low blast radius.

## Excluded adjacencies

`/v1/security/api-keys/*` is a **different subsystem** (`APIKey` ->
`tenant_api_keys`, `SecurityService`, `security.router`) from auth's `ApiKey`
-> `api_keys`. It is excluded and recorded in
`selected-out-of-scope-adjacent-routes.csv`. Already-protected auth routes
(`mfa/setup`, `logout`, `sessions/{session_id}`) are explicitly excluded so the
implementation slice cannot re-open closed work.

## Product decisions required

None blocking. One question to confirm during implementation: whether
`POST /v1/auth/impersonate` should be restricted to `super_admin` only or also
`admin_security` (see product-decisions-required.md).
