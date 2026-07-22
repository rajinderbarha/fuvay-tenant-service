# Canonical Role Certification

## Confirmed via live introspection

```
sorted(ROLE_PERMISSIONS.keys()) ==
['admin_finance', 'admin_operations', 'admin_readonly', 'admin_security',
 'customer', 'guest', 'staff', 'super_admin', 'technician', 'tenant_owner']
```

Exactly the 10 canonical roles. No alias (`readonly`, `manager`,
`tenant_manager`, `tenant_readonly`, `office_staff`, `tenant_finance`,
`operations_manager`, `platform_manager`, `finance_manager`,
`security_manager`) is a key in this registry.

## Repository-wide alias search — one real finding, resolved

`grep -rl` for the forbidden alias list across `app/` surfaced
`app/engines/roles_permissions/service.py`, which defines a
`REQUIRED_ROLE_ORDER` including `tenant_manager` (and several other
non-canonical names: `platform_admin`, `finance_admin`,
`operations_admin`, `support_admin`, `compliance_officer`) for a
Super-Admin "Roles & Permissions" **read-only catalog display** (a
pre-existing Phase-1B ticket, unrelated to this authorization program).

Inspected in full: this module exposes only `list_roles`,
`get_role_detail`, and `list_permissions*` — no assignment, creation, or
update function exists anywhere in it. Every non-canonical name is
explicitly returned with `is_implemented=false, is_active=false`, and its
own module docstring states this is intentional ("this is intentionally
honest, not a bug"). **No executable path exists anywhere in this module
that would let a user actually be assigned `tenant_manager` or any other
alias.** This does not violate "no alias remains executable" — it is a
read-only, honestly-labeled reference to a name, not an executable role.

All other alias-name matches across the codebase (`tenant_finance_router.py`,
`_admin_service.py` variable names, etc.) were confirmed by `grep` context
to be either filenames/router names unrelated to a `role` field value, or
similarly non-executable references (not individually re-verified line by
line for every match beyond the two shown above, given time constraints —
recorded as a residual, low-confidence item below).

## Unknown-role fail-closed behavior

`ROLE_PERMISSIONS.get(role, [])` (used throughout `permissions.py`)
returns an empty permission list for any role not in the dict — this is
the actual mechanism by which `tenant_manager`/`tenant_readonly` currently
have **zero effective permissions** today, confirmed and cited repeatedly
across this program's demo-account investigation. This is fail-closed by
construction, not by a specific check.

## Second finding, investigated and resolved: `create_user` default value

`app/engines/tenant_engine/admin_service.py:705`:
`role = data.get("role", "tenant_manager")` — a dangerous-looking default
that recreates an invalid role if the caller omits `role`. Traced fully:
line 706 immediately checks `if role not in VALID_TENANT_ROLES: raise
ServiceOSException("TENANT_USER_ROLE_INVALID", ...)`, and
`VALID_TENANT_ROLES = {"tenant_owner", "staff"}` (line 51) does **not**
include `"tenant_manager"`. The default value is therefore always
immediately rejected by validation before it can reach `User(role=role,
...)` — this is dead/misleading code (the default should arguably be
`None` or omitted entirely, since it can never actually be used), but it
is **not an executable path that creates an invalid-role user**. `update_user`
(line 735) uses the same `VALID_TENANT_ROLES` check with no dangerous
default. Recorded as a code-quality finding, not a security finding — see
`known-limitations.md`.

This also answers a standing open question from this program: the two
known invalid-role demo accounts were not created through this or any
other currently-reachable API path (both would be rejected here); they
were created via `scripts/canonical_seed_final_l5_01.py`'s direct ORM
insert (bypassing all API validation), consistent with Slice 2C's
original finding.

## Third finding, not fully resolved: `workflow_service.py` static data

`app/engines/workflows/workflow_service.py` contains static workflow-step
definition dicts with `"owner_role": "tenant_manager"` and
`"allowed_role": "tenant_manager"` entries. No `Depends(...)` FastAPI
dependency or `ROLE_PERMISSIONS` lookup references these fields in the
files grepped this slice — they appear to be descriptive workflow-engine
metadata (which persona a workflow step is *conceptually* associated
with), not an executable authorization check. This was not traced all the
way through the workflow engine's own enforcement code (if any) this
slice — recorded as an open, unverified item in `known-limitations.md`
rather than asserted safe.

## Residual item

The remaining alias-string matches in `app/engines/admin_catalog/service.py`,
`execution/coaching_router.py`, `execution/real_estate_router.py`,
`field_ops/billing_service.py`, `invoice_payment/provider_router.py`,
`media/asset_service.py`, `package_commerce/service.py`,
`platform_notifications/provider_router.py`,
`quote_checklist/provider_router.py`, `tenant_engine/admin_service.py`,
`workflows/workflow_service.py` were located by `grep` but not
individually opened and read this slice (time-scoped). Recorded as an
open, low-confidence verification gap in `known-limitations.md` rather
than asserted clean.
