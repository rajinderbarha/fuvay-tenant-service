# Customer Self-Service Dependency Semantics

## `require_tenant_mutation_permission` (app/core/permissions.py, line ~872)

```python
def require_tenant_mutation_permission(permission: str) -> Callable:
    role_check = require_permission(permission)

    async def _check(user = Depends(get_current_user)) -> UserContext:
        user = await role_check(user)  # role-based permission gate (admits any role with the grant)
        if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
            raise ServiceOSException("PERMISSION_DENIED", ...)
        return user
    return _check
```

| Aspect | Behavior |
|---|---|
| Admitted roles | Any role granted the given permission in `ROLE_PERMISSIONS` (e.g. `BOOKING_CANCEL` → `customer` and `tenant_owner`) |
| Customer branch | No distinct code branch — a customer simply never carries `access_scope` (see below), so the second `if` is always false for a real customer account and the dependency degenerates to a plain permission check |
| Tenant branch | For a tenant-side role (`tenant_owner`, etc.), the second `if` additionally denies when `access_scope in {"customer_support_limited"}` |
| Access-scope behavior | `access_scope` is a JWT claim (`app/dependencies/auth.py` line 43); populated only for tenant-side accounts that carry it in their token payload. Customer token issuance does not set this claim — confirmed no code path sets `access_scope` for `role="customer"` tokens. |
| Permission behavior | Delegates entirely to `require_permission` (role-based `ROLE_PERMISSIONS` lookup + `permission_overrides`) — unchanged from the base dependency |
| Principal tenant behavior | Not checked by this dependency at all — object-level tenant/customer ownership (does this Booking belong to THIS caller) is enforced separately at the service layer (`_assert_can_access_booking`) |
| Customer identity behavior | Not derived here — `self.actor_id`/`self.actor_role` are set from `UserContext` in the service constructor, server-derived from the JWT, never client-suppliable |
| Explicit-deny behavior | `access_scope in TENANT_READONLY_ACCESS_SCOPES` is the only explicit deny condition; `super_admin` is exempted |
| Unknown-role behavior | An unknown role fails the underlying `require_permission` check first (no permission grant exists for an undefined role in `ROLE_PERMISSIONS`) — fails closed before reaching the access_scope check |
| Unknown-scope behavior | Any `access_scope` value not in `TENANT_READONLY_ACCESS_SCOPES` (including `None`) passes the check — this is intentional: only the ONE known read-only scope value is denied, everything else (including genuinely unknown/malformed scope strings) is treated as "not read-only" and allowed through the SCOPE gate (object-ownership is still enforced separately) |
| Route-specific ownership | NOT enforced by this dependency — each service method's own `_assert_can_access_booking`/`_assert_owns`-style check is the actual ownership boundary |

## Is this the right dependency for dual customer/tenant routes?
**Yes, and it is already correctly independent of tenant mutation scope for customers** — not because of an explicit "customer branch," but because customers structurally never carry the one `access_scope` value this dependency denies. This was proven directly (not just by source inspection) in `tests/test_phase2f15b_booking_creation_provenance_and_customer_dependency.py::TestCustomerDependencyIndependentOfTenantScope`:
- A customer `UserContext` with `access_scope=None` passes.
- A customer `UserContext` with a FORGED `access_scope="customer_support_limited"` (an adversarial edge case that cannot occur via real token issuance) is correctly denied — fail-closed, not a silent bypass, even in that scenario.
- A `tenant_owner` with read-only `access_scope` remains denied (regression-proof — this must not change).
- `super_admin` remains exempt (regression-proof).

## Should any route use a different dependency instead?
No route reclassification is needed:
- `create_booking`/`cancel_booking`/`request_reschedule` (`DUAL`) correctly use `require_tenant_mutation_permission` — it is the SAME dependency for both personas because the permission itself (`BOOKING_CREATE`/`BOOKING_CANCEL`/`BOOKING_RESCHEDULE`) is dual-granted; there is no separate `require_customer`-only dependency in the codebase that would also need to be satisfied for the tenant side, and vice versa.
- Tenant-only routes (`confirm_booking`, `reject_booking`, `convert_to_job`, `accept_reschedule`, `reject_reschedule`) correctly use the same dependency with a tenant-only-granted permission (`BOOKING_MANAGE`/`TENANT_UPDATE`) — a customer without that permission grant fails the underlying `require_permission` check regardless of `access_scope`.
- `add_note` correctly uses `require_staff_or_above_mutation` (a role-list dependency, not permission-based) since no permission-based dual grant exists for note-adding.

## Tenant roles cannot enter a customer-only ownership branch
There is no "customer-only ownership branch" in `require_tenant_mutation_permission` at all — ownership is enforced identically for every role at the SERVICE layer (`_assert_can_access_booking`), which explicitly switches on `self.actor_role`: `customer` → own-booking-only; tenant-scoped roles → own-tenant-only; unknown → denied. A `tenant_owner` can never reach the `customer` branch of that switch (it is an `if/elif` on role, not a shared code path).
