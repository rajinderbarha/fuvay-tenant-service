# Verifier Negative Fixture Report

`verify_2f37.py --selftest` re-run fresh in this worktree: 21/21 "fires
when violated" (identical to 2F-38's result — the same rules, same
detectors, unaffected by this slice's test/seed-only changes).

`test_phase2f39_seed_role_guard.py`'s own negative-fixture coverage: all
10 alias/manager/readonly variants, empty string, and mixed-case are each
proven to raise `ValueError` **before** `db.execute` is awaited
(`db.execute.assert_not_awaited()` on a mock configured to raise if
touched at all) — this is a real, executed negative fixture per rejected
value, not a single generic assertion.
