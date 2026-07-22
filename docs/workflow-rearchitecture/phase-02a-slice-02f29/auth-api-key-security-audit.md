# Auth API-Key Security Audit - Slice 2F-29

Applies **only** to `ApiKey -> api_keys` (`app.engines.auth`). The
`/v1/security/api-keys/*` subsystem (`APIKey -> tenant_api_keys`,
`SecurityService`) is a **different** subsystem and was not touched - asserted
by `test_separate_security_subsystem_untouched`.

## Evidence

| Property | Evidence |
|---|---|
| Tenant + id scoping | `WHERE ApiKey.id == key_id AND ApiKey.tenant_id == tenant_id` on update and revoke |
| Not mutable by id alone | same predicate; a foreign key never matches |
| State validated | `revoked_at == None` in the predicate, so revoke/update of an already-revoked key raises NotFound |
| Foreign/missing key | `NotFoundException` - no existence oracle |
| Tenant/actor authority | both come from the token, never from the body |
| Raw secret exposure | `full_key` returned **only** by create (documented one-time contract); absent from update and revoke |
| Storage | `hashed_key=hashed`; raw material is never persisted |
| Access scope | now enforced by `require_tenant_mutation_permission(auth:apikeys:manage)` |

Client control of owner/tenant/creator/revoker fields is not possible: those
are function parameters supplied from the authenticated context.
