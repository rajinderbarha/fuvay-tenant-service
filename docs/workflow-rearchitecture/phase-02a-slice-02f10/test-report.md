# Test Report — Slice 2F-10

## New tests
`tests/test_phase2f10_customer_complaints_authorization.py` — **25
passed**. Covers: router-level role gate (unauthenticated, every denied
role x mutation routes, every denied role x read routes, super_admin
non-wildcard, correct-customer-clears-gate) + direct service-layer IDOR/
ownership/ordering-defect tests (creation ownership, refund ownership,
resolution cross-complaint IDOR, `_get_resolution` unit tests, ordering
defect for both accept and reject, rework-creation-not-triggered proof).

## Targeted regression
```
python -m pytest tests/test_phase2f10_customer_complaints_authorization.py \
  tests/test_phase2f9_complaints_provider_authorization.py \
  tests/test_phase2f9a_complaints_state_machine.py -q
```
**139 passed.**

## Fixture updates (pre-existing tests, not new failures)
Two pre-existing tests broke against the new, correct `create_complaint`
ownership check because their mocked DB fixtures never stubbed record
ownership (a scenario that didn't previously need to be modeled):
- `tests/test_sprint25_complaints.py::test_create_complaint_success`
- `tests/test_sprint75_dispute_settlement.py::test_create_complaint_sets_sla_deadlines`

Both updated to stub `ComplaintEligibilityService._fetch_record`
returning a record owned by the test's customer_id — both now pass.

## Broader partition
```
python -m pytest tests/ -k "complaint or settlement or rework or refund or customer_support" -q
```
Excluding 10 test files that require a live Postgres connection
unreachable in this sandboxed environment (`ConnectionRefusedError`,
confirmed pre-existing and unrelated — none touch `customer_router` or
any file this slice modified): **342 passed, 0 failed.**

Including those 10 live-DB files (for full transparency, not to claim
they passed): 15 failed (all `ConnectionRefusedError` to a real DB
socket), 1051 passed, 2 skipped, 5 errored (same DB-connectivity cause).
None of the 15 failures or 5 errors reference `complaints.customer_router`,
`complaint_service.py`, `refund_service.py`, or the mutation-inventory
tool — confirmed by direct inspection of each failing test's traceback.

## Runtime verification
```
inventory_mutation_routes.py --verify-module app.engines.complaints.customer_router
```
→ `{"total_routes": 8, "unverified_count": 0, "unverified_routes": []}`
(down from 8 unverified before this slice's fixes).
```
inventory_mutation_routes.py --verify-module app.engines.complaints.provider_router
```
→ unchanged, `{"total_routes": 9, "unverified_count": 0}`.

## Frontend
No frontend file was changed this slice (see
`frontend-customer-exposure-audit.md`) — TypeScript checking and linting
were therefore not run, per the instruction to run them "only when
frontend files change."

## Summary
All new and targeted regression tests pass. The broader partition passes
cleanly once the pre-existing, environment-caused live-DB test failures
are excluded and separately accounted for — not silently hidden.
