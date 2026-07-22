# Worktree Interference Guard — Slice 2F-39A4

`cert_guard_2f39a4.py` checks worktree path, git-dir, branch, `cea399f`
ancestry, and expected HEAD before every write/commit/test invocation —
same pattern as prior slices, with one structural fix.

## Fix applied: expected_head no longer goes stale

Per the Slice 2F-39A3 review, the prior guards' `expected_head` state file
was committed inside the worktree, so it went stale immediately after any
commit following an `--update-head` sync (each such sync itself needed a
further commit, which then made the just-synced value stale again).

This guard stores `expected_head` at
`G:/serviceos-2f37r-preserve/cert_guard_2f39a4_state.json` — outside the
committed worktree entirely. Updating it after a commit requires no further
repository commit, so it cannot go stale relative to HEAD. Verified working
in this slice: after committing the 9 defect fixes (`8a62bba`),
`--update-head` synced cleanly with no residual `git status` change.

Never fired `CONCURRENT_WORKTREE_INTERFERENCE` this slice.
