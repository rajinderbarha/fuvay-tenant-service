# Eligibility/Creation Consistency — Slice 2F-10A (Workstream 6/12)

## Fix
`create_complaint` now calls
`self._eligibility.check_eligible(db, customer_id, record_type, record_id,
complaint_type=complaint_type, category_id=category_id)` as its sole
eligibility gate, raising `ValueError(eligibility["reason_code"] or
ERR_COMPLAINT_NOT_ELIGIBLE)` before any `CustomerComplaint` row is
constructed if `eligibility["eligible"]` is falsy.

## Why a single shared assertion, not duplicated rules
Per the mission's explicit preference (Workstream 6), `create_complaint`
does not re-implement status/window/duplicate logic — it delegates
entirely to `ComplaintEligibilityService.check_eligible`, the same method
the advisory `check-eligible` endpoint calls. There is exactly one
implementation of every eligibility rule in the codebase, reached from
both the preflight read path and the creation mutation path.

## Consistency proof
`test_phase2f10a_complaint_eligibility_and_refund_integrity.py::TestEligibilityCreationConsistency`:
- `test_ineligible_fixture_blocks_both_check_and_create` — runs the exact
  same fixture through both `check_eligible` directly and through
  `create_complaint` (via a stub returning `check_eligible`'s own real
  result), proving both reject it identically.
- `test_eligible_fixture_allows_both_check_and_create` — same for an
  eligible fixture.
- `test_create_complaint_never_persists_when_ineligible` — proves, for
  each of the 4 reason-code families
  (`ERR_COMPLAINT_ACCESS_DENIED`/`ERR_COMPLAINT_NOT_ELIGIBLE`/
  `ERR_COMPLAINT_WINDOW_EXPIRED`/`ERR_COMPLAINT_DUPLICATE_OPEN`), that
  `db.add`/`db.commit` are never called.

Because `create_complaint` calls `check_eligible` directly (not a
re-derived copy of its logic), the two are structurally incapable of
disagreeing for the same fixture — this is a stronger guarantee than
"we tested a few cases and they matched."
