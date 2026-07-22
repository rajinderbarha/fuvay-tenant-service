# Documentation Corrections

While rebaselining historical tests for the live canonical CSV move
(264/241/23 → 273/252/21), discovered and corrected two pre-existing
maintenance gaps, neither introduced by this slice:

1. `tests/test_phase2f31_n01_media_closure.py::test_canonical_and_matrix_hash`
   had stale hardcoded hashes (`1f7891798eb8382f` / `abac4ae72e8ab1d4`,
   leftover from 2 slices prior) that had apparently never been updated
   since — corrected to the current values as part of this slice's
   rebaseline pass.
2. 18 historical test files (2F-14A, 2F-17A, 2F-19, 2F-21, 2F-23, 2F-25,
   2F-25A, 2F-26, 2F-26B) asserted the live canonical CSV's total/protected/
   unprotected counts inline rather than against a frozen snapshot; each
   was individually updated at its exact assertion line (never a blanket
   find/replace) to the new 273/252/21 figures, with a one-line comment
   attributing the change to this slice. No frozen point-in-time slice
   artifact (CSV, hash, or historical claim) was rewritten.
