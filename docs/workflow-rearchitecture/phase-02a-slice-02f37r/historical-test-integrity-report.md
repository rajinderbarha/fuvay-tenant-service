# Historical Test Integrity Report — Slice 2F-37R-A

## Modified historical test files this slice

Exactly one pre-existing test file was edited:
`tests/test_phase2f26e_classifier_repair.py`, one assertion
(`TestCanonicalFrozen.test_migration_144_remains_unapplied`).

Classification: **explicit `PROTECTED_BY_LATER_SLICE` override**, following
the same discipline established in Slices 2F-35/36/37 (see
`docs/workflow-rearchitecture/phase-02a-slice-02f37/regression-report.md`,
"Classifier reclassification notes").

## Why this is not an improper historical rewrite

- The original assertion's *literal* implementation (grep `git status
  --porcelain` output for the migration filename) is changed.
- The assertion's *stated intent* (docstring: "must not be in the applied
  chain") is preserved exactly — the new implementation checks the same
  real-world fact (migration 144 has not been run against a database) via
  a direct, more accurate proxy (file presence + absence of an application
  marker) instead of an indirect one (git-tracked-status) that this slice's
  own committed-baseline goal permanently breaks.
- No historical point-in-time claim (a prior slice's documented pass/fail
  count, coverage arithmetic, or dated evidence) was altered. Only a
  currently-executing assertion's implementation detail changed, in the
  currently-running test suite, with an inline comment explaining exactly
  why and citing this slice by name — the established pattern throughout
  this program.

## Collection count reconciliation

No test was added, removed, or renamed by this slice. Collection remains
2445 (matching the previously-documented 2F-37 baseline) across both
regression runs in `phase2f-regression-report.md`.
