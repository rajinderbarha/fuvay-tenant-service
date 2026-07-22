# Slice 2F-39A2R — Implementation Summary

## Final status: `AUTHORIZATION_REMEDIATION_BLOCKED`

This slice resolved all 6 authorization defects Slice 2F-39A2 found and
deliberately did not force-fix, per the explicit review directive
("Resolve the six known defects before continuing with the remaining
149-route census").

## What was achieved

1. **API-key sibling group revalidated** across both subsystems: 2F-39A's
   `auth.router` trio reconfirmed safe (unchanged, fresh re-verification);
   2F-39A2's `security.router::create_api_key` fix reconfirmed;
   `security.router`'s `rotate_api_key`/`revoke_api_key` reconfirmed safe
   (already using `_require_trusted_tenant` since Slice 2F-35); a new
   finding surfaced (`list_api_keys`/`get_api_key` read-path gap, recorded
   not fixed).
2. **Intended caller model determined** for `record_activity`,
   `write_audit`, `create_session`, `revoke_session`: zero internal
   callers exist for any of the 4 (grep-confirmed), and 3 of the 4 were
   already documented as unremediated authorization observations since
   Slice 2F-26D/F/G/H — explicitly deferred there to "a future slice to
   select, prove and close properly." This is that slice.
3. **All 4 fixed** with server-derived identity/tenant checks:
   - `record_activity`/`write_audit_entry`: tenant_id now cross-checked
     via the existing `_require_trusted_tenant` helper.
   - `create_session`: `user_id` must match the caller's own identity.
   - `revoke_session` (HIGH severity, the single highest-signal item in
     the 2F-26 observation corpus): session ownership now verified
     before revocation; foreign sessions are treated identically to
     missing ones (non-oracular).
4. **`activate_rule`/`deactivate_rule` fixed** — found to have **zero**
   tenant scoping at all (worse than 2F-39A2's original "guard mismatch"
   classification), now matching the sibling `update_rule`/`delete_rule`
   pattern already established in the same file.
5. **13 new tests** prove every fix; 1 existing test
   (`test_revoke_session_deletes_redis_first`) updated under an explicit
   `PROTECTED_BY_LATER_SLICE`-style comment, since its assertion
   literally enshrined the pre-fix, insecure design.

## Evidence

- Phase-2F regression: 2494/2494 passed, twice, identical.
- Full backend regression: see `full-backend-regression-diff.md`.
- Only 3 application files changed (`security/service.py`,
  `pricing/router.py`, `pricing/service.py`) plus 2 test files.

## Net effect on the certification ledger

Confirmed unresolved authorization defects: 6 → **0**. Cumulative
unresolved route count remains 149 (unchanged — out of this slice's
scope by design). This slice stops at its own approval gate; Slice
2F-39A3 may now resume route classification.
