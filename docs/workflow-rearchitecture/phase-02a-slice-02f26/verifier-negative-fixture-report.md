# Verifier Negative-Fixture Report — Slice 2F-26

A verifier that cannot fail proves nothing. These fixtures prove this one can.

## Fixtures

| Fixture | Asserts |
|---|---|
| `test_verifier_passes_on_the_current_tree` | `main()` returns 0 today |
| `test_failing_condition_is_recorded` | an injected false condition lands in `FAILURES` |
| `test_docstring_cannot_satisfy_a_source_check` | a function whose **docstring** mentions `db.add(` and `tenant_id`, but whose body does neither, yields neither token after `strip_prose()` |
| `test_where_inspection_is_not_vacuous` | `str(unscoped_stmt)` **contains** `tenant_id` (the trap), while `where_clause(unscoped_stmt)` does **not**; and `where_clause(scoped_stmt)` does |

## Why exactly these

Both are traps this initiative fell into for real:

- **2F-24** asserted `Depends(get_current_user)` was absent and matched a
  *comment* describing its removal.
- **2F-25A** asserted `ServiceJob` was absent and matched a *docstring* saying
  it is not used.
- **2F-25** asserted `"tenant_id" in str(stmt)` to prove tenant scoping — which
  passes for a completely unscoped query, because every `SELECT reviews.*`
  lists that column. It was caught only because the *negative* case (super
  admin, expected unscoped) failed for the same reason.

The fixtures encode those exact failure modes so a future refactor cannot
quietly reintroduce them.

## Result
All 4 fixtures pass, alongside the 38 other tests in
`test_phase2f26_application_wide_inventory.py`.
