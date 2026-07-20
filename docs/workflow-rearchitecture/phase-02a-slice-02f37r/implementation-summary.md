# Slice 2F-37R-A — Implementation Summary

## Status: `RECOVERED_CONSOLIDATED_BASELINE_COMMITTED`

This slice resumed the interrupted Slice 2F-37R recovery from its
preserved forensic state, isolated the work in a dedicated worktree after
confirming a second process was actively committing to the shared main
worktree, completed changed-path classification (0 UNKNOWN), built and
verified a consolidated backend recovery baseline, found and fixed two
real defects the verifier/regression suite caught, and confirmed the
final state with two clean, identical full regression runs plus two
clean, identical verifier runs.

## Workstream outcomes

- **WS1 (quarantine):** confirmed a second `claude` host process, running
  since before this session started, is the credible source of the
  earlier unattributed checkout/commit on the shared main worktree. See
  `active-process-quarantine.md`. No process was terminated.
- **WS2 (dedicated worktree):** `G:/serviceos-phase2f-recovery` on
  `security/phase-2f-authorization-recovered`, created from
  `recovery/phase-2f-uncommitted-snapshot @ e0652e2`. See
  `dedicated-worktree-evidence.md`.
- **WS3 (guard):** `recovery_guard_2f37ra.py` run before every write,
  commit, verifier, and regression command; never reported
  `CONCURRENT_WORKTREE_INTERFERENCE`.
- **WS4 (preservation reverification):** patch/archive/bundle checksums
  recorded; bundle re-verified "okay". Originals untouched.
- **WS5 (base confirmation):** `4ce23c5` reconfirmed as an ancestor of the
  recovery HEAD via `git merge-base --is-ancestor`.
- **WS6 (classification):** 3,001 changed paths, 0 UNKNOWN (after
  resolving 5 initial ambiguous paths). See
  `changed-path-classification.csv`, `unknown-path-resolution.md`.
- **WS7 (strategy decision):** Strategy B (consolidated) selected and
  justified. See `recovery-strategy-decision.md`.
- **WS8 (reconstruction):** consolidated commit built, then corrected
  twice after real defects surfaced during its own verification (a
  boot-breaking file exclusion, and 47 wrongly-deleted-instead-of-reverted
  base files). See `recovered-branch-report.md`.
- **WS9 (historical test discipline):** one test assertion fixed under an
  explicit `PROTECTED_BY_LATER_SLICE: 2F-37R-A` marker. See
  `historical-test-integrity-report.md`.
- **WS10 (canonical recomputation):** 313/313 protected/denominator, 0
  unprotected, independently re-derived by `verify_2f37.py`'s live route
  introspection against the committed tree. See
  `canonical-state-reconciliation.md`.
- **WS11 (verifier re-execution):** `verify_2f37.py` 21/21 PASS, run twice
  against the final commit, identical both times.
- **WS12 (regression completion):** `tests/test_phase2f*.py` 2445/2445
  passed, 0 failed, run twice, identical. See `phase2f-regression-report.md`,
  `deterministic-test-report.md`.
- **WS13 (committed final baseline):** commit `d00f723` on
  `security/phase-2f-authorization-recovered`, clean working tree. See
  `recovered-branch-report.md`.
- **WS14 (UX-05 non-interference):** confirmed no writes to UX-05 by this
  slice; UX-05 continued advancing on its own concurrently and
  independently. See `ux05-preservation-report.md`.
- **WS15 (blockers preserved):** neither demo account nor Migration 144
  was touched. See `role-remediation-blocker.md`, `migration-runtime-blocker.md`.

## Final status token

**`RECOVERED_CONSOLIDATED_BASELINE_COMMITTED`**

Criteria met: final recovered authorization state is complete, attributable
(0 UNKNOWN paths), committed, and independently verified; canonical state
is 313/313 with 0 unprotected; final verifier and full regression pass
(twice, identically); UX-05 remains separate and untouched. Criterion not
met for the stronger `RECOVERED_SLICE_2F37_BASELINE_COMMITTED` token: exact
per-slice (2F-34/35/36/37) commit boundaries were not credibly
reconstructable, by design of Strategy B — see `recovery-strategy-decision.md`.

## Recommended next step

Slice 2F-38 may be restarted from `security/phase-2f-authorization-recovered`
@ `d00f7230f98236c96dd21e1498c78779dc209e7b`, the only commit this slice
certifies as a valid starting point. This slice stops at its own approval
gate; Slice 2F-38 is not restarted in this run.
