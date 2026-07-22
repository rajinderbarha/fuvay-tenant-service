# Regression Report — Slice 2F-10A (Workstream 14)

## Targeted
```
python -m pytest tests/test_phase2f10a_complaint_eligibility_and_refund_integrity.py \
  tests/test_phase2f10_customer_complaints_authorization.py \
  tests/test_phase2f9_complaints_provider_authorization.py \
  tests/test_phase2f9a_complaints_state_machine.py -q
```
**164 passed** (25 new + 25 + 84 + 30 from prior slices, unchanged).

## Broader partition (deterministic, excluding live-DB-only files)
```
python -m pytest tests/ -k "complaint or settlement or rework or refund or customer_support" \
  --ignore=<10 live-DB files, see live-database-test-limitations.md> -q
```
**367 passed** (up from Slice 2F-10's 342 — the 25 new tests).

## Runtime verification (unchanged)
- `complaints.customer_router`: `{"total_routes": 8, "unverified_count": 0}`.
- `complaints.provider_router`: `{"total_routes": 9, "unverified_count": 0}`.

## Confirmed unchanged from Slice 2F-10
- `require_customer` role enforcement on all 15 customer_router routes.
- Complaint/booking-job ownership checks.
- Refund-request complaint ownership (Slice 2F-10's fix).
- Resolution complaint-ID cross-check (`_get_resolution`).
- Settlement proposal complaint-ID cross-check (`_get_settlement_proposal`,
  Slice 2F-9's shared fix).
- Resolution validation-before-mutation ordering fix.
- No `ServiceReworkRequest` commit on an illegal resolution transition.
- Monetary settlement remedies blocked; dual acceptance required.
- Tenant mutation coverage: 106/182, unchanged.

## Fixture updates required by this slice's `create_complaint` change
Two pre-existing tests and one Slice 2F-10 test previously stubbed only
`_fetch_record`/`_customer_owns_record` (the narrower Slice 2F-10 check);
updated to stub `check_eligible` directly, matching the new single-gate
design:
- `tests/test_sprint25_complaints.py::test_create_complaint_success`
- `tests/test_sprint75_dispute_settlement.py::test_create_complaint_sets_sla_deadlines`
- `tests/test_phase2f10_customer_complaints_authorization.py::TestComplaintCreationOwnership::test_create_complaint_rejects_unowned_record`/`test_create_complaint_allowed_for_owned_record`

All updated tests pass; no test was weakened — each still proves the
same ownership/eligibility guarantee, just through the new call surface.
