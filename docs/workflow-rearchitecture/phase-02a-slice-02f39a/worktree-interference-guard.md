# Worktree Interference Guard

`cert_guard_2f39a.py` (same pattern as every prior slice's guard) checked
worktree path, git-dir, branch, `26b0109` ancestry, and expected HEAD
before every write/commit/test invocation. Never fired
`CONCURRENT_WORKTREE_INTERFERENCE` this slice.
