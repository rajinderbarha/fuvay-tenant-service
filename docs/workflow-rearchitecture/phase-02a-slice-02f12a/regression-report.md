# Regression Report — Slice 2F-12A (Workstream 13)

No source file was changed this slice (verify-and-document only).

## New cancellation tests
`tests/test_phase2f12a_coaching_cancellation.py` — **27 passed** (test
executions, not unique-only totals): HTTP-level cancellation persona
matrix + service-level business-wide/tenant-ownership/state/reason
proofs + direct source comparison.

## Slice 2F-12 + siblings + 2F-3B
```
python -m pytest tests/test_phase2f12a_coaching_cancellation.py \
  tests/test_phase2f12_coaching_authorization.py \
  tests/test_sprint21_execution.py \
  tests/test_phase2f3b_execution_assignment_mutation_enforcement.py -q
```
**198 passed** (test executions across overlapping partitions).

## Complaint + real-estate closure regression subset
```
python -m pytest tests/test_phase2f9_complaints_provider_authorization.py \
  tests/test_phase2f10_customer_complaints_authorization.py \
  tests/test_phase2f11_real_estate_authorization.py \
  tests/test_phase2f11a_real_estate_read_privacy.py -q
```
**155 passed.**

## Runtime verification
`inventory_mutation_routes.py --verify-module app.engines.execution.coaching_router`
→ `{"total_routes": 8, "unverified_count": 0, "unverified_routes": []}`
— unchanged.

## Confirmed unchanged
- All 8 mutation route guards intact (`require_owner_or_office_staff_mutation`).
- The 7 assignment checks (`_assert_staff_owns_appt`) intact.
- Technician denied from every mutation and read.
- Provider reads owner/staff only (`require_owner_or_office_staff_read`).
- Customer tracking customer-only + ownership filtered.
- State validation before mutation (`_set_status` → `_assert_transition`).
- Final states protected.
- `app.engines.coaching_appointment` unmodified.
- Global tenant mutation coverage: 125/182.

## Overlapping partitions
The 198 and 155 figures above are **test executions across overlapping
partitions**, not unique-test totals (`test_sprint21_execution.py` and
`test_phase2f12_coaching_authorization.py` appear in more than one run).
