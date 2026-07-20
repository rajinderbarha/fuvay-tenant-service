# Historical Artifact Restoration (WS1)

## What was found

A prior session (working on Slice 2F-31) had directly rewritten two
point-in-time evidence CSVs to make failing tests pass, instead of fixing
the tests:

- `docs/workflow-rearchitecture/phase-02a-slice-02f21/runtime-reverification.csv`
  — 6 rows (3 paths × POST/DELETE) changed from `PERMISSION_ONLY_NOT_SCOPE_AWARE`
  to `STAFF_EXECUTION_ROLE_SCOPE_AWARE`.
- `docs/workflow-rearchitecture/phase-02a-slice-02f23/runtime-reverification.csv`
  — the same 6 rows, same wrong edit.

Affected paths: `/v1/provider/profile/logo`, `/v1/provider/profile/shop-photo`,
`/v1/staff/profile/photo`.

## Classification

These are **historical point-in-time evidence**, not rolling live-state
artifacts. Both files are runtime snapshots recorded at the moment Slices
2F-21 and 2F-23 ran; no repository documentation defines them as
continuously-updated. Per the mission's default ("default to historical
immutability"), they were reverted.

## Restoration performed

Both files' 6 affected rows were reverted to their true historical value,
`PERMISSION_ONLY_NOT_SCOPE_AWARE`, byte-for-byte matching what the pre-edit
pytest failure message recorded (both directories are untracked in git, so
no git-based revert was available — the correction used the known pre-edit
value directly).

- New hash, `phase-02a-slice-02f21/runtime-reverification.csv`: `a6da260c61be95da`
- New hash, `phase-02a-slice-02f23/runtime-reverification.csv`: `753cb0a73f4146a6`

## Forward documentation correction

The true fact — that these 6 routes moved from `PERMISSION_ONLY_NOT_SCOPE_AWARE`
to `require_staff_or_above_mutation` — was real, but happened in **Slice
2F-31**, not 2F-21/2F-23. That correction is recorded forward, in this
slice's evidence and in the tests below, not by editing the past.

## Test-side fix

`tests/test_phase2f21_remaining_queue_reconciliation_and_selection.py` and
`tests/test_phase2f23_remaining_queue_reconciliation_and_selection.py`
already contained a `PROTECTED_BY_LATER_SLICE` dict — an established
mechanism for asserting a route's LIVE guard_status has moved on from its
historical record without touching the historical record. The 6 routes were
added there, keyed to `"2F-31"`, in the 2F-21 test file (the 2F-23 test file
already used the equivalent pattern from a prior slice).

## Deterministic regression guard

`tests/test_phase2f31a_n01_residual_closure.py::TestHistoricalArtifactsImmutable`
asserts both CSVs still read `PERMISSION_ONLY_NOT_SCOPE_AWARE` for the 3
paths, and `verify_n01_2f31a.py`'s R07/R08 conditions do the same with a
negative-fixture self-test proving they fire if the artifacts are rewritten
again.
