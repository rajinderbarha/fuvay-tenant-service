# Test Report — Slice 2F-14C

## New tests

`tests/test_phase2f14c_field_ops_notes_media_and_create_job_fk.py` — 12 tests, all passing:

- `TestNoteMediaRouterGuardSources` (2) — source-verifies `require_staff_or_above_mutation` is
  wired on both `add_note` and `add_media`.
- `TestNoteMediaOwnershipStillEnforced` (2) — re-verifies the pre-existing Slice 2F-14A
  object-ownership checks are intact underneath the new router guard.
- `TestCreateJobLinkedRecordOwnership` (8) — foreign/missing `service_type_id`, inactive
  `service_type_id`, foreign/missing `parent_job_id`, foreign `booking_id`, foreign/missing
  `customer_id`, and a no-persistence-on-rejection proof.

All fixtures are deterministic (`MagicMock`/`AsyncMock` with explicit `side_effect` sequencing
matching the exact order of DB calls in `create_job`) — behavior is proven by direct service
invocation, not source-string assertion (only `TestNoteMediaRouterGuardSources` uses source
inspection, to confirm wiring).

## Regression

See regression-report.md — 243 passed across direct slice/dependency suites; 1276 passed in the
broad partition sweep; 15 pre-existing live-environment exclusions honestly disclosed and not
counted as passing. Two pre-existing test files (`test_phase2f14b_...py`,
`test_job_type_flows.py`) required fixture updates to supply additional mock DB responses for
`create_job`'s new validation calls — documented in regression-report.md, not silent.
