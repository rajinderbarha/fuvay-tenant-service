# Canonical Dependency Semantics — `require_owner_or_office_staff_mutation`

## Exact admitted roles
```python
if user.role not in ("super_admin", "tenant_owner", "staff"):
    raise ServiceOSException(error_code="PERMISSION_DENIED", ...)
```
A strict allow-list of exactly 3 literal role strings. No other string — including `"office_staff"`, `"tenant_manager"`, `"manager"`, `"supervisor"`, `"technician"`, `"customer"`, `"guest"`, or any fabricated/unknown role — is ever admitted. Proven directly (not just by source read) via `TestCanonicalDependencyRoles` (`tests/test_phase2f16a_quote_invoice_lineage_and_read_privacy.py`):
- `test_admits_only_canonical_roles` — `super_admin`/`tenant_owner`/`staff` all pass.
- `test_denies_prohibited_aliases` — `office_staff`/`tenant_manager`/`manager`/`supervisor` all denied.
- `test_denies_technician_and_customer` — `technician`/`customer`/`guest` all denied.
- `test_denies_unknown_role` — a fabricated role string denied.

## Role normalization
None performed — `user.role` is compared by exact string equality against the allow-list tuple. No case-folding, no alias-mapping table, no synonym resolution exists anywhere in this function.

## The function's NAME contains "office_staff" but the CODE does not accept it as a role value
The function is named `require_owner_or_office_staff_mutation` — "office staff" here is a descriptive/documentation term for what `staff` role users typically do (back-office work), not a literal role string the function checks for. Per the mission's explicit allowance ("The helper name may remain legacy if changing it would be broad, but behavior must not admit a prohibited alias"), this slice did NOT rename the function (a broad, cosmetic change affecting every other call site across the codebase that already uses this dependency from prior slices) — it only verified and proved that the BEHAVIOR admits canonical roles exclusively.

## Permission check
None — this is a pure role-list dependency (no `permission_checker.has(...)` call), unlike `require_tenant_mutation_permission` which wraps a specific permission. `StaffPermission` effective-permission integration does not apply to this dependency at all (it never consults `StaffPermission` overrides) — this is consistent with its purpose as a coarse role gate for capabilities with no dedicated permission constant.

## Access-scope enforcement
```python
if user.role != "super_admin" and getattr(user, "access_scope", None) in TENANT_READONLY_ACCESS_SCOPES:
    raise ServiceOSException(...)
```
Denies any tenant-side user (not `super_admin`) whose `access_scope` is `"customer_support_limited"` — proven by `test_denies_readonly_access_scope`.

## Explicit deny precedence
The role check runs FIRST (before the access-scope check) — an unauthorized role is denied before access_scope is even examined, consistent with fail-closed ordering used throughout this codebase.

## Super-admin handling
Explicitly exempted from the access-scope check (`user.role != "super_admin"` guard) — proven by `test_super_admin_exempt_from_readonly_scope`. Super_admin is NOT exempted from the role check itself (it must still literally be `super_admin`, which it always is when it reaches this branch).

## Unknown role/scope handling
Unknown role → denied by the allow-list `not in (...)` check (fails closed). Unknown access_scope value (anything other than the one literal `"customer_support_limited"` string) → NOT denied by the access-scope check specifically (only that one value is checked), but such a role would already need to have passed the role allow-list first — there is no scenario where an "unknown scope" bypasses authorization entirely, since the role check is the primary gate and object-level ownership (tenant_id matching) remains the ultimate authority underneath.

## Conclusion
`require_owner_or_office_staff_mutation` admits canonical tenant roles only. No prohibited alias (`office_staff`, `tenant_manager`, `manager`, `supervisor`) is accepted as an actual role value despite the function's descriptive name.
