# Worktree Interference Guard

`cert_guard_2f39a3.py` checked worktree path, git-dir, branch, `293d7f5`
ancestry, and expected HEAD before every write/commit/test invocation.
Never fired `CONCURRENT_WORKTREE_INTERFERENCE` this slice.
