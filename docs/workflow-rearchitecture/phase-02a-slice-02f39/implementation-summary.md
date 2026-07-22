# Slice 2F-39 — Implementation Summary

## Final status: `AUTHORIZATION_REMEDIATION_BLOCKED`

This slice resumed from Slice 2F-38's honest blocked baseline
(`ba01d15`) and targeted its specific, evidenced blockers rather than
re-attempting certification. See `final-status-rationale.md` for exactly
why this token was chosen over `ROLE_REMEDIATION_POLICY_BLOCKED` (route
census incomplete, not just role/migration).

## What was fixed, with root cause

1. **Live seed-script security gap (the headline finding from 2F-38)**:
   `scripts/canonical_seed_final_l5_01.py::get_or_create_user()` had zero
   role validation. Fixed with a fail-closed guard
   (`_require_canonical_role`, backed by `CANONICAL_ROLES` derived from
   `app.core.permissions.ROLE_PERMISSIONS`), and removed the two call
   sites that hardcoded `"tenant_manager"`/`"tenant_readonly"` — the exact
   source of this program's two known invalid-role demo accounts. 28 new
   tests prove it (every alias/empty/mixed-case variant rejected before
   any database call; every canonical role accepted; existing-user
   mismatches surfaced, never silently promoted).
2. **A second live instance of the same gap**, found by auditing beyond
   the one function 2F-38 discovered: `scripts/seed_demo_users.py::upsert_user()`
   unconditionally set `user.role = role` on an existing user with zero
   validation. Fixed with the same pattern.
3. **The actual root cause of the one test-order-dependent failure**:
   `test_dispatch_job_sync.py` monkeypatched `DocumentService.generate_document`
   directly onto the class and only ever restored `__init__` in teardown,
   permanently replacing the method with a test stub for the rest of the
   process — this, not any code regression, caused
   `test_phase2f35_critical_authorization_batch.py`'s intermittent
   failure. Fixed by restoring both patched attributes.
4. **17 of the original 45 full-backend failures resolved**, each with an
   identified, documented root cause (fixture drift after legitimate
   2F-36 tenant-context hardening, a legitimate `require_staff_or_technician_only`
   refactor, a legitimate HTTP-410 endpoint retirement, a legitimate
   route-deduplication fix, and one genuinely stale Phase-2D historical
   test-count assertion never updated across 2F-35/36/37/38). See
   `complete-backend-regression-report.md`.

## What remains blocked

- Mounted-route census: 261/2320 routes still unclassified — this
  slice's own deliberate scope decision (see `route-census-reproduction.md`),
  not a new finding.
- Both demo accounts remain `MANUAL_ROLE_CONFIRMATION_REQUIRED` — no new
  evidence, no human decision received.
- Migration 144 remains unproven in PostgreSQL — environment unavailable.
- 28 full-backend failures remain, individually dispositioned in
  `remaining-failure-disposition.csv` (13 pre-existing domain issues, 2
  frontend version-pin drifts from concurrent unrelated work, 2 TS-compile
  checks, 2 flagged as possibly authorization-adjacent and worth
  prioritizing next).

## Evidence

- `verify_2f37.py`: 21/21 PASS, reconfirmed at start and end of this
  slice — 313/313 canonical mutations remain protected throughout every
  change this slice made.
- Phase-2F regression: 2473/2473 passed, twice, identical.
- Complete backend regression: 12,124 collected, 12,075 passed, 28
  failed (down from 45), 21 skipped — one run, honestly reported.

This slice stops at its own approval gate. Final application-wide
certification is not attempted in this run.
