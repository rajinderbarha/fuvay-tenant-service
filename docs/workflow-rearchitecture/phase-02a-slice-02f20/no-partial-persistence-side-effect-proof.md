# No Partial Persistence / Side Effect Proof

## For every rejected mutation (all 6 selected routes)
Every one of the 6 routes performs ALL validation (role/scope dependency,
`_require_tenant`, rate-limit check, allow-list validation, tenant-scoped
object lookup, legal-state check) BEFORE any `db.add`/attribute mutation,
and calls `await db.commit()` exactly once, at the very end, after every
check has passed — unchanged, pre-existing structure, re-confirmed by
code read for all 6 handlers this slice.

| Rejected scenario | Where it fires | Persists? |
|---|---|---|
| Read-only tenant owner (dependency layer) | `require_tenant_owner_mutation`, before the route body ever executes | No — FastAPI dependency resolution raises before the handler runs at all |
| Invalid `consent_type` (withdraw_consent) | Allow-list check, before rate-limit/service call | No |
| Rate limit exceeded | `_check_rate_limit`, before the service call | No |
| Invalid `request_type` (create_my_request) | Allow-list check, before duplicate check/service call | No — and now this allow-list check actually SUCCEEDS for legitimate values (this slice's fix), rather than always failing |
| Missing `confirm_understanding`/`reason` | Explicit checks, before service call | No |
| Duplicate open request | Tenant-scoped duplicate check, before service call | No |
| Cross-tenant `request_id` (cancel/generate-export/*_response/download) | `if not req: raise NOT_FOUND`, before any mutation | No |
| Invalid legal state (cancel_my_request wrong status; generate_export wrong status/type) | Explicit state check, before any mutation | No |

## New this slice — explicitly re-verified
- `create_request`'s atomic `metadata_json` write means a REJECTED create
  (failing validation before reaching `create_request` at all) writes
  NOTHING — and even a SUCCESSFUL create never has an intermediate
  unscoped state, closing the prior non-atomic window.
- `revoke_consent`'s `tenant_id` fix does not change WHEN persistence
  happens (still one commit, at the end) — only WHAT value is persisted.

## Direct test coverage
`test_metadata_json_passed_to_model_constructor` and
`test_missing_metadata_json_defaults_to_empty_dict_not_none` directly
prove the CONSTRUCTOR-level atomicity (the object passed to `db.add` ALREADY
carries the correct `metadata_json` — there is no code path where
`db.add` is called with an unscoped object that gets patched later).

## No export worker task queued / no file generated / no storage object created
Trivially true for EVERY case (rejected or not) — confirmed by
`compliance-export-worker-discovery.md`: no such mechanism exists in this
codebase to queue, generate, or store anything, so no rejected (or even
successful) call can ever produce these side effects.

## No notification success event
Confirmed — none of the 6 routes trigger any notification (email/SMS/
push/in-app) — this module has no delivery integration at all.

## No commit where validation precedes persistence
Confirmed for all 6 routes — single `await db.commit()` call at the end
of each handler, always after every validation check.
