# API-Key Sibling Group Revalidation

## Precise clarification (correcting an ambiguity, not a false claim)

There are **two entirely separate, independently-implemented API-key
subsystems** in this codebase, confirmed distinct since Slice 2F-34
("Separate security API-key subsystem... confirmed still separate"):

1. **`app/engines/auth/router.py`** — `/v1/auth/api-keys*` — tenant
   integration keys, backed by `AuthService`. This is the trio Slice
   2F-39A classified and added to the canonical denominator
   (`create_api_key`, `revoke_api_key`, `update_api_key`), with 4
   dedicated tests.
2. **`app/engines/security/router.py`** — `/v1/security/api-keys*` —
   a separate key subsystem, backed by `SecurityService`. This is where
   Slice 2F-39A2 found and fixed the real defect in `create_api_key`.

**These are not the same route, the same service, or the same table.**
Slice 2F-39A's "correctly protected" conclusion was about the `auth`
subsystem's three routes. Slice 2F-39A2's defect was in the unrelated
`security` subsystem's `create_api_key`. Neither conclusion was actually
false about the route it described — but the review's concern that
"the earlier conclusion may not generalize to siblings" was exactly
right in spirit, so every route in both subsystems is independently
reverified below, fresh, in this slice.

## Revalidation results (all reverified fresh this slice, not assumed)

### `auth.router` trio (2F-39A's original scope) — CONFIRMED SAFE, unchanged

| Route | Guard | Tenant source | Verdict |
|---|---|---|---|
| `POST /v1/auth/api-keys` (`create_api_key`) | `require_tenant_mutation_permission(P.AUTH_APIKEYS_MANAGE)` | `user.tenant_id` (server-derived), explicit `if not user.tenant_id: raise` | SAFE |
| `DELETE /v1/auth/api-keys/{key_id}` (`revoke_api_key`) | same | same | SAFE |
| `PATCH /v1/auth/api-keys/{key_id}` (`update_api_key`) | same | same | SAFE |

### `security.router` sibling group (2F-39A2's scope) — mixed, now fully reconciled

| Route | Guard | Tenant source | Verdict |
|---|---|---|---|
| `POST /v1/security/api-keys` (`create_api_key`) | Was `require_permission` + client body `tenant_id` | **FIXED in 2F-39A2** (commit `7eaeca8`): now `require_tenant_mutation_permission` + server-derived `u.tenant_id` | NOW SAFE |
| `POST /v1/security/api-keys/{key_id}/rotate` (`rotate_api_key`) | `require_tenant_mutation_permission(P.TENANT_UPDATE)` | Router passes a client **Query** `tenant_id`, but `SecurityService.rotate_api_key` calls `self._require_trusted_tenant(tenant_id)` before any query — server-side cross-check already exists (added Slice 2F-35, per the code's own comment) | SAFE, reconfirmed |
| `POST /v1/security/api-keys/{key_id}/revoke` (`revoke_api_key`) | Same guard | Same `_require_trusted_tenant` pattern (Slice 2F-35) | SAFE, reconfirmed |
| `GET /v1/security/api-keys/tenants/{tenant_id}` (`list_api_keys`) | `require_permission(P.TENANT_UPDATE)` (bare, not tenant-mutation) | Client path param `tenant_id`, **no cross-check found in `SecurityService.list_api_keys`** | **READ-PATH GAP, not a mutation defect** — a read-only-scoped or wrong-tenant caller could list another tenant's API key names/prefixes (not the raw key). Recorded, not fixed (out of this slice's mutation-remediation scope; consistent with the pricing/read-path precedent). |
| `GET /v1/security/api-keys/{key_id}` (`get_api_key`) | Same bare `require_permission` | Client Query `tenant_id`, same gap as `list_api_keys` | Same read-path gap, recorded not fixed |
| `POST /v1/security/api-keys/verify` (`verify_api_key`) | No user auth at all — `Depends(get_db)` only | N/A — verifies a raw API key by its own HMAC hash, which is itself the credential (analogous to a webhook signature check) | Correctly public by design; not a gap |

## Supersession entry (added to the cumulative ledger, not rewriting history)

> The Slice 2F-39A `create_api_key` protection assessment concerned
> `app/engines/auth/router.py::create_api_key` (the tenant-integration
> API-key subsystem) and remains correct, reconfirmed fresh in this
> slice. It did **not** describe `app/engines/security/router.py::create_api_key`
> (a separate subsystem), which Slice 2F-39A2 found genuinely broken and
> fixed. No historical Slice 2F-39A artifact is edited by this note —
> this is a clarifying addition to the cumulative record, not a
> retraction of a false claim.

## New finding this slice: `list_api_keys` / `get_api_key` read-path gap

Both use `require_permission(P.TENANT_UPDATE)` (not
`require_tenant_mutation_permission`, and these are reads so that guard
distinction is less relevant) with a client-supplied `tenant_id` and no
service-layer cross-check against the caller's own tenant. This is a
**read-path privacy gap**, structurally identical in kind to the
already-documented `run_preflight`/`replay_snapshot` findings from
2F-39A2 — not a mutation-authorization defect, and consistent with this
program's standing, explicitly out-of-mutation-scope read-path
limitation. Recorded in `known-limitations.md`, not fixed this slice.
