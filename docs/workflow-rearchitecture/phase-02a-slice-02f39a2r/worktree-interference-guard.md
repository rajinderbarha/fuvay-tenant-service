# Worktree Interference Guard

`cert_guard_2f39a2r.py` checked worktree path, git-dir, branch, `fca8a96`
ancestry, and expected HEAD before every write/commit/test invocation.
Never fired `CONCURRENT_WORKTREE_INTERFERENCE` this slice.
