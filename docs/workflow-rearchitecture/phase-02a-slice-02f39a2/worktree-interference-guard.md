# Worktree Interference Guard

`cert_guard_2f39a2.py` checked worktree path, git-dir, branch, `dbeaf42`
ancestry, and expected HEAD before every write/commit/test invocation.
Never fired `CONCURRENT_WORKTREE_INTERFERENCE` this slice.
