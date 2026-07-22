# Worktree Interference Guard

`cert_guard_2f39.py` checks: absolute worktree path, git-dir suffix,
current branch, `ba01d15` ancestry, and (after the first run) expected
HEAD, failing with `CONCURRENT_WORKTREE_INTERFERENCE` on any mismatch. Run
before every write/commit/test invocation this slice. Never fired.

One operational note: the guard's own state file
(`cert_guard_2f39_state.json`) was found empty/corrupt once mid-session
(a JSON decode error), traced to an interrupted prior invocation rather
than external interference — deleted and reinitialized, confirmed the
branch/HEAD were still exactly as expected before continuing.
