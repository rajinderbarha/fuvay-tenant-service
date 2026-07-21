# Seed Role Negative Tests

`tests/test_phase2f39_seed_role_guard.py` — 28 tests, all passing:

- `TestCanonicalRolesRegistry` (2): `CANONICAL_ROLES` equals the exact
  10-role set; derived from `ROLE_PERMISSIONS`, not a second list.
- `TestRequireCanonicalRoleRejectsBeforeDbCall` (10 alias/manager/readonly
  variants + empty + mixed-case + 10 valid-role-acceptance parametrized
  cases = 23): every alias (`tenant_manager`, `tenant_readonly`, `manager`,
  `readonly`, `office_staff`, `tenant_finance`, `operations_manager`,
  `finance_manager`, `security_manager`, `platform_manager`), an empty
  string, and a mixed-case variant (`"Staff"`) are all rejected **before**
  `db.execute` is ever awaited (proven via `db.execute.assert_not_awaited()`
  / a `MagicMock` configured to raise `AssertionError` if touched); all 10
  canonical roles are accepted and reach the `INSERT`.
- `TestExistingUserRoleMismatch` (2): a matching role is a quiet skip; a
  mismatched role is surfaced in output and the row is never written to
  (`db.execute.await_count == 1`, i.e. `SELECT` only, no `UPDATE`/`INSERT`).
- `TestIdempotency` (1): repeated calls with the same canonical role
  return the same id, zero extra writes.
- `TestManagerReadonlyNoLongerSeeded` (1): confirms the two hardcoded
  call-site literals are gone from source (not merely unreachable).

All 28 pass; see `phase2f-regression-report.md` for their inclusion in the
Phase-2F suite total (2445 → 2473).
