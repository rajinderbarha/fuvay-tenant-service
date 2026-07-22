# Test Quality Report

- Every one of the 34 new tests has at least one negative-path or
  bypass-prevention counterpart where applicable (see
  `TestNonOracularResponses`, `TestNoBypassOfClosedRoutes`).
- No test in `test_phase2f35_critical_authorization_batch.py` asserts on
  mocked internals only — each service-layer test asserts the actual
  WHERE-clause/query shape sent to a `MagicMock` DB (the same `_where()`-
  style discipline used throughout this program), not just "no exception
  raised."
- Two false-positive `git grep` bypass checks were caught and hardened
  during authoring (see Errors and Fixes in prior slice work):
  `AuthService.revoke_api_key` name collision, and a stray untracked
  `.py.tmp.*` editor-crash artifact — both now explicitly filtered/
  excluded with a comment explaining why.
- Verifier self-test (`--selftest`) confirms all 22 R01-R22 conditions
  actually fail when forced false — no condition is a silent no-op.
