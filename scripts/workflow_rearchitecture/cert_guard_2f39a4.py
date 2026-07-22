"""Slice 2F-39A4 worktree guard.

Fixes the expected_head staleness defect flagged in the Slice 2F-39A3
review: the mutable expected_head state is now stored OUTSIDE the
committed worktree (in the external preservation directory), so
updating it never requires a further repository commit and can never
itself go stale relative to HEAD.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EXPECTED_WORKTREE = "G:/serviceos-phase2f39a4-product-decision"
EXPECTED_GITDIR_SUFFIX = "worktrees/serviceos-phase2f39a4-product-decision"
EXPECTED_BRANCH = "security/phase-2f39a4-product-decision-remediation"
EXPECTED_BASE_COMMIT = "cea399f"
STATE_FILE = Path("G:/serviceos-2f37r-preserve/cert_guard_2f39a4_state.json")


def sh(*args: str) -> str:
    return subprocess.check_output(["git", *args], text=True).strip()


def main() -> int:
    update_head = "--update-head" in sys.argv
    toplevel = sh("rev-parse", "--show-toplevel").replace("\\", "/")
    gitdir = sh("rev-parse", "--git-dir").replace("\\", "/")
    branch = sh("branch", "--show-current")
    head = sh("rev-parse", "HEAD")

    failures = []
    if toplevel.rstrip("/").lower() != EXPECTED_WORKTREE.lower():
        failures.append(f"worktree path mismatch: {toplevel!r} != {EXPECTED_WORKTREE!r}")
    if EXPECTED_GITDIR_SUFFIX.lower() not in gitdir.lower():
        failures.append(f"git-dir mismatch: {gitdir!r}")
    if branch != EXPECTED_BRANCH:
        failures.append(f"branch mismatch: {branch!r} != {EXPECTED_BRANCH!r}")
    try:
        sh("merge-base", "--is-ancestor", EXPECTED_BASE_COMMIT, "HEAD")
    except subprocess.CalledProcessError:
        failures.append(f"{EXPECTED_BASE_COMMIT} is not an ancestor of HEAD")

    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    expected_head = state.get("expected_head")
    if expected_head is not None and not update_head and head != expected_head:
        failures.append(f"HEAD moved unexpectedly: {head!r} != recorded {expected_head!r}")

    if failures:
        print(json.dumps({"result": "CONCURRENT_WORKTREE_INTERFERENCE", "failures": failures}, indent=2))
        return 1

    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps({"expected_head": head, "branch": branch, "toplevel": toplevel}, indent=2))
    print(json.dumps({"result": "OK", "worktree": toplevel, "branch": branch, "head": head}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
