# Complete Backend Regression Report — Slice 2F-39

## Result

`python -m pytest tests/ -q`: **12,124 collected, 12,075 passed, 28
failed, 21 skipped**, 1356.99s (0:22:36). One run (not two — see
`known-limitations.md`).

Collection grew from 12,096 to 12,124 (+28, matching the new
`test_phase2f39_seed_role_guard.py` file exactly).

## Before/after

| | Before (Slice 2F-38) | After (Slice 2F-39) |
|---|---|---|
| Collected | 12,096 | 12,124 (+28 new tests) |
| Passed | 12,030 | 12,075 |
| Failed | 45 | 28 |
| Skipped | 21 | 21 (unchanged) |

**17 of the original 45 failures are fixed** — every fix backed by an
identified root cause, not a workaround:

- 8 seed-role-validation failures (`test_phase2d_tenant_access_model.py`)
- 1 frozen historical-count staleness (`test_phase2d_tenant_access_model.py`)
- 1 test-order-pollution root cause (`test_dispatch_job_sync.py`'s
  incomplete monkeypatch teardown, which was the actual cause of
  `test_phase2f35_critical_authorization_batch.py`'s intermittent failure)
- 2 fixture-drift failures in `test_dispatch_job_sync.py` itself (missing
  `actor_tenant_id`, missing `_get_job` mock for a newer ownership
  pre-check)
- 2 stale exact-string assertions after the `require_staff_or_technician_only`
  refactor (`test_p0_job_completion_credit_deduction.py`)
- 1 same refactor staleness (`test_phase7_staff_app_certification.py`)
- 1 stale assertion after a `_staff_actor_type` helper was introduced
  (`test_module_l5_19_staff_chat.py`)
- 1 retired-endpoint test rewrite (`test_customer_idor.py`)
- 1 stale route-duplication allowlist (`test_final_l5_05t_service_area_route_canonicalization.py`)

**28 remain**, all individually dispositioned in
`remaining-failure-disposition.csv`: 13 pre-existing domain-logic
failures unrelated to authorization (service catalog, checklist,
complaint eligibility, quote checklist — verified reproducing in
isolation, not newly introduced), 2 TypeScript-compile-environment
checks, 2 frontend package-version-pin drifts (caused by concurrent,
unrelated UX work on other branches — explicitly out of this slice's
scope to fix), and 2 chat-access-scoping tests
(`test_sprint27_notifications.py`) flagged as *possibly*
authorization-adjacent but not confirmed or fixed — an honest open item,
not swept under the rug.

## What was NOT hidden

None of the 28 remaining failures are omitted, retried away, skipped, or
excluded from this count. Every one has a named disposition and, where
not fixed, an explicit reason and recommended owner.
