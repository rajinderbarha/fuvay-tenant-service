# Final Commit Evidence

| Field | Value |
|---|---|
| Branch | `security/phase-2f-authorization-recovered` |
| Worktree | `G:/serviceos-phase2f-recovery` |
| Final commit | `ed804e091fa76b18f90e66e88cc2f67be5fb6a4c` |
| Parent | `d00f7230f98236c96dd21e1498c78779dc209e7b` |
| Base ancestor (proven via `git merge-base --is-ancestor`) | `4ce23c5` |

## Full commit chain, base to tip

1. `4ce23c5` — recovery base (design/ux-05-staff-technician-app, pre-authorization-program)
2. `e1ef86b` — forensic snapshot (Slice 2F-37R)
3. `e0652e2` — forensic snapshot, CRLF-normalization follow-up
4. `29dd931` — consolidated backend baseline (Strategy B), initial exclusion pass
5. `532190d` — correction: restored 2 boot-critical files wrongly excluded
6. `dc7e936` — correction: reverted 47 excluded-but-base-existing files to base content
7. `d00f723` — `PROTECTED_BY_LATER_SLICE` fix to one obsolete historical test assertion
8. `ed804e0` — final Slice 2F-37R-A documentation set

Verified via `git log --oneline security/phase-2f-authorization-recovered`
and cross-checked against `recovery_guard_2f37ra.py`'s recorded
`expected_head` at each deliberate update, which never diverged from this
sequence.

## Evidence this commit is what it claims to be

- `verify_2f37.py`: 21/21 PASS, executed twice against this exact commit
  (once immediately after `d00f723`, once again for final confirmation),
  identical results.
- `tests/test_phase2f*.py`: 2445 collected, 2445 passed, 0 failed, 0
  errors — two independent runs (484.38s, 399.32s), identical outcome.
- `changed-path-classification.csv`: 3,001 paths classified against the
  base→snapshot diff, 0 UNKNOWN.
