# Worktree Interference Guard — Slice 2F-39A5

`cert_guard_2f39a5.py` checks worktree path, git-dir, branch, `d960ac5`
ancestry, and expected HEAD before every write/commit/test invocation,
using the same externally-stored `expected_head` state fix introduced in
`cert_guard_2f39a4.py` (state lives at
`G:/serviceos-2f37r-preserve/cert_guard_2f39a5_state.json`, outside the
committed worktree, so it never goes stale relative to HEAD after a
commit).

Never fired `CONCURRENT_WORKTREE_INTERFERENCE` this slice.
