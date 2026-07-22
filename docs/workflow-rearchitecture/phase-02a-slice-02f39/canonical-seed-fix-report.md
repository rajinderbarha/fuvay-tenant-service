# Canonical Seed Fix Report

## `scripts/canonical_seed_final_l5_01.py`

- Added `CANONICAL_ROLES` (derived from `ROLE_PERMISSIONS`) and
  `_require_canonical_role()`, called as the first line of
  `get_or_create_user()` — invalid role fails before any `db.execute`.
- `get_or_create_user` now selects `role` alongside `id` for existing
  users, and if the existing row's role differs from the requested role,
  prints an explicit `[SKIP] ... role mismatch ... NOT modified` line and
  returns the existing id **without ever writing to the row** — no
  silent promotion.
- Removed the two call sites that hardcoded `"tenant_manager"`/
  `"tenant_readonly"` for `manager@`/`readonly@demo-ac-services.local`.
  No canonical replacement is assigned (none is authorized — see
  `demo-account-decision-packet.md`); a comment explains why and points
  to the decision packet.
- Idempotency preserved: re-running with a canonical role and an
  already-matching existing row is a pure `[SKIP]`, zero writes (proven
  in `test_phase2f39_seed_role_guard.py::TestIdempotency`).
- Password handling unchanged (`hash_password`, no plaintext logging).
- Logs never print `hashed_password` or session tokens (unchanged).

## `scripts/seed_demo_users.py`

- Added the same `CANONICAL_ROLES` derivation and an inline guard at the
  top of `upsert_user()`, before any database read or write.
- This script's `DEMO_USERS` literals (`super_admin`, `tenant_owner`,
  `technician`, `customer`) are all canonical, so behavior is unchanged
  for its current, actual callers — the fix is purely defensive hardening
  against any future caller passing an invalid value, closing the same
  class of gap 2F-38 found.
- This script's existing "upsert" (update-in-place) semantics for
  matching canonical roles were intentionally left unchanged — that is
  this tool's documented purpose ("Idempotent: upserts users by email"),
  distinct from `canonical_seed_final_l5_01.py`'s stricter
  never-touch-existing-role semantics. Both are now equally safe against
  invalid role values; they differ (by design, pre-existing, unchanged)
  in how they handle an existing user with a *canonical but different*
  role.

## Not modified

`app/engines/tenant_engine/admin_service.py` (`create_user`/`update_user`)
— already correctly validates against `VALID_TENANT_ROLES` before any
write; confirmed unchanged.
`scripts/seed_admin_roles_final_l5_05l.py` — confirmed safe by
construction; not retrofitted (see `canonical-role-validation-contract.md`).
