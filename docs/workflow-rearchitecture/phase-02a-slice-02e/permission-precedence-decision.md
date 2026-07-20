# Permission Precedence Decision

## Decision: use the existing, already-correct precedence in `PermissionChecker.has()` — no new precedence rule was invented

Per the brief's own instruction ("do not invent precedence rules if the model, tests, or existing documentation already define them"): they were already defined, just unreachable. The existing order is:

1. `super_admin` → always true (no override can reduce this — by design, platform super-admin is not tenant-scoped and has no `StaffPermission` rows loaded regardless)
2. `P.ALL` in role bundle → true
3. **Exact permission-key override → returns the override's value directly (grant or deny)** — this is where "explicit deny overrides grant" lives, and it was already correct
4. Engine-wildcard override (`"field_ops:*"` etc.) → same
5. Role bundle membership → true
6. Else → false (fail closed)

## Why this order is safe
- **Explicit deny overrides a grant for the same permission**: satisfied — step 3 returns unconditionally once a match is found, whether `True` or `False`, and step 3 runs before step 5's role-bundle check.
- **Tenant overrides must never apply outside their tenant**: satisfied structurally — overrides are loaded `WHERE user_id = :user_id`, and `user_id` belongs to exactly one `tenant_id` (enforced by the `User` model itself), so there is no code path where one tenant's override dict could contain another tenant's grants.
- **Unknown permissions must not become effective**: satisfied — the `permission` argument to `.has()` is always a hardcoded `P.*` constant supplied by route code (e.g. `require_permission(P.STAFF_MANAGE)`), never a value taken from the override dict's keys or any user input. An override row with a typo'd `permission_key` simply never matches any real permission check — it's inert, not a security hole (confirmed and now actively monitored by `check_role_integrity.py`'s unknown-permission-key check).
- **Permission-source failure must not silently grant access**: if `_get_staff_permissions`' query fails, the exception propagates rather than being caught and defaulted to `{}` — confirmed by reading the method (no try/except wraps it).

## What was NOT changed
No new precedence tier was added. No "template" precedence layer was introduced (the brief explicitly warns against a template becoming a hidden role alias — none was built). The fix this slice made is purely about *reaching* the existing, already-correct logic (closing the `get_current_user` gap), not about redesigning the logic itself.
