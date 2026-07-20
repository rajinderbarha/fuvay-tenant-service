# Test Report — Slice 2F-9A

## New tests (this slice)
`tests/test_phase2f9a_complaints_state_machine.py` — **30 passed**.
Covers: full final-state matrix for both routes (11 statuses x 2 routes
minus non-applicable combinations), repeated-action classification,
audit-event proof, side-effect safety, and 3 drift-guard tests.

## Targeted regression (Slice 2F-9 + complaints core)
```
tests/test_phase2f9_complaints_provider_authorization.py
tests/test_module_l5_02_complaint_sla_job.py
tests/test_module_l5_02_complaints_flow.py
tests/test_module_l5_24_complaint_notify.py
tests/test_sprint25_complaints.py
tests/test_phase2f9a_complaints_state_machine.py
```
**166 passed, 1 skipped** (pre-existing).

## Broader partition (complaints/settlement/rework/refund/credit/security-deposit)
```
python -m pytest tests/ -k "complaint or settlement or rework or refund or credit or security_deposit" -q
```
**681 passed, 4 skipped** (pre-existing), 9970 deselected.

## Frontend
`npx tsc --noEmit` in `frontend/tenant-portal` — clean, no output, no
errors.
`next lint` — **not verified** (pre-existing environment/tooling gap:
no ESLint v9 flat config exists in this environment; documented in prior
slices, not silently skipped).

## Runtime verification
`inventory_mutation_routes.py --verify-module app.engines.complaints.provider_router`
→ `{"total_routes": 9, "unverified_count": 0, "unverified_routes": []}`.

## Not run
Full repository test suite was not run in full (would exceed the scope
and time proportional to a narrow follow-up slice); the targeted +
broader partitions above cover every test file that imports or exercises
`complaint_service.py`, `provider_router.py`, `rework_service.py`,
`refund_service.py`, and complaint-adjacent notification/SLA/credit
paths.
