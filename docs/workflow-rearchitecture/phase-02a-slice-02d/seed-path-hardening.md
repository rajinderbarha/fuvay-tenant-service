# Seed Path Hardening

## Changes to `scripts/canonical_seed_final_l5_01.py`

### 1. Canonical-role guard added
`get_or_create_user()` now raises `ValueError` (before any database call) if `role` is not one of the 10 canonical values. Proven via `tests/test_phase2d_tenant_access_model.py::TestSeedScriptCanonicalGuard` — 6 parametrized invalid-role rejections, each asserted to reject *before* `db.execute` is ever called (using a mock DB that raises `AssertionError` if touched).

### 2. Manager/read-only demo personas removed, replaced honestly
Previously seeded `manager@demo-ac-services.local` (`tenant_manager`) and `readonly@demo-ac-services.local` (`tenant_readonly`) — both invalid. Per Workstream 5's explicit instruction ("read-only demo users must not be created until the access model is proven," "manager-like demo users must use a canonical role plus proven permission configuration"), and given this slice's finding that neither the manager permission model nor the read-only enforcement model is fully proven today, both personas are removed rather than replaced with a misleading substitute. A single `staff@demo-ac-services.local` account (real, canonical `staff` role) is seeded instead, honestly representing the base staff bundle — not a stand-in for "manager" or "read-only."

### 3. Related bug fixed: admin demo accounts
Independently discovered this slice: the same script's 3 non-super-admin platform demo accounts (`admin.ops@`, `admin.finance@`, `admin.readonly@serviceos.local`) were seeded with `role="super_admin"`, relying on a separate one-off script (`seed_admin_roles_final_l5_05l.py`) to correct them after the fact. Fixed at the source — now seeds `admin_operations`/`admin_finance`/`admin_readonly` directly, plus adds the previously-never-seeded `admin_security@serviceos.local` account. The follow-up script becomes an idempotent no-op rather than a required second step for a fresh environment.

## Idempotency
`get_or_create_user()`'s existing SELECT-then-INSERT pattern is unchanged — a second run still SKIPs any email that already exists. Not independently re-verified via a full live re-run this slice, since the script has its own destructive-reset safety gate (`ALLOW_DATABASE_RESET=true` required) that was deliberately not overridden (see `known-limitations.md`) — verified via static code review and the unit-level guard tests instead.

## Testing
`tests/test_phase2d_tenant_access_model.py::TestSeedScriptCanonicalGuard` — 8 tests total (6 parametrized rejections + 1 canonical-set match + 1 accept-and-query-DB proof).

## Not changed
No other seed script in `scripts/` was found writing an RBAC role value (confirmed via the Slice 2C/2D role-write-path audit) — this is the one remaining unvalidated write path, now closed.
