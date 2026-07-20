# Scope-Only Mutation Access Guard Evidence (WS2)

## Why a new guard, not an existing one

`app/core/permissions.py` was searched for an existing scope-only mutation
guard before adding one. The existing `require_*_mutation` family
(`require_tenant_owner_mutation`, `require_staff_or_above_mutation`,
`require_owner_or_office_staff_mutation`, `require_tenant_mutation_permission`)
all combine a **role restriction** with the read-only-access-scope check —
none of them admit an unrestricted role set. `POST /v1/media/upload` and
`POST /v1/media/{media_id}/replace` are intentionally mixed-persona
(a customer uploading their own media, alongside tenant staff uploading
business assets) — replacing their guard with any of these would have
silently dropped customer access, which the mission explicitly forbade.
No existing helper fit, so one was added, per WS2's explicit permission.

## The guard

```python
async def require_mutation_access_scope(
    user: UserContext = Depends(get_current_user)
) -> UserContext:
    if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
        raise ServiceOSException(...)
    return user
```

- Wraps `get_current_user` — **every** role `get_current_user` admits is
  still admitted. Verified by `tests/test_phase2f31a_n01_residual_closure.py
  ::TestScopeOnlyMutationGuard::test_guard_does_not_narrow_admitted_roles`,
  which asserts the FastAPI `Depends` default's `.dependency` is literally
  `get_current_user`.
- Rejects read-only mutation scope using the same
  `TENANT_READONLY_ACCESS_SCOPES = {"customer_support_limited"}` set every
  other `*_mutation` guard uses, and the same before-body-parsing timing
  (it's a `Depends`, so it runs before the route handler reads the request
  body).
- Rejects unknown scope implicitly: only membership in
  `TENANT_READONLY_ACCESS_SCOPES` is denied; every other value (including
  `None` for customers, who have no `access_scope`) passes through
  unaffected — consistent with every other `*_mutation` guard's behavior.
- Adds/changes no permission: it does not touch `permission_checker` or
  `StaffPermission` at all.
- Preserves `StaffPermission` explicit-deny behavior: N/A for these two
  routes (neither used `require_tenant_mutation_permission` before or
  after), and no `StaffPermission` logic was touched.
- No parallel authorization framework: it is one more function in the same
  file, following the exact shape of its siblings.

## Admitted-role-set proof

Live introspection (`authority_model_2f26e.py`) before/after:

| Route | Guard before | Admitted roles before | Guard after | Admitted roles after |
|---|---|---|---|---|
| `POST /v1/media/upload` | `get_current_user` | all authenticated | `require_mutation_access_scope` | all authenticated (identical) |
| `POST /v1/media/{media_id}/replace` | `get_current_user` | all authenticated | `require_mutation_access_scope` | all authenticated (identical) |

The only behavioral change: a principal with `access_scope=
"customer_support_limited"` can no longer call either route. No other
persona is affected.
