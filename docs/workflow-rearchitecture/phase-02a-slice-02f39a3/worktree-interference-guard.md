# Worktree Interference Guard

`cert_guard_2f39a3.py` checked worktree path, git-dir, branch, `293d7f5`
ancestry, and expected HEAD before every write/commit/test invocation.

## Known mechanism defect (flagged in Slice 2F-39A3 review)

The guard's `expected_head` is written to a JSON state file that is
itself committed to the worktree. Because updating that file requires
its own commit, `expected_head` is stale (one commit behind true HEAD)
immediately after every `--update-head` call that is followed by any
further commit — including a commit of the state file's own update.
This produced several apparent `CONCURRENT_WORKTREE_INTERFERENCE`
findings in this slice's closeout that were not real interference: each
was reconciled by checking `git log`/`git reflog` for author, timestamp,
and ancestry, confirming the "unexpected" HEAD move was this session's
own prior commit, not a foreign process.

**This is not an acceptable steady-state behavior for future
certification slices.** Before Slice 2F-39B or any later slice reuses
this guard pattern, the mechanism must be changed to one of:
- store the mutable `expected_head` state outside the committed
  worktree (e.g., in the external preservation directory), or
- derive the expected state from the immutable base commit plus an
  approved ancestry list rather than a single trailing pointer, or
- update `expected_head` without requiring a further repository commit.

Until corrected, every apparent interference finding must continue to be
manually reconciled against reflog, author, timestamp, and exact diff —
never auto-dismissed.
