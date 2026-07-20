"""Slice 2F-37R-A recovery guard.

Fails fast if the dedicated recovery worktree's identity drifts: wrong
directory, wrong branch, wrong git-dir, or (before a deliberate update)
wrong HEAD. Run before every write/commit/verifier/regression step.

Usage:
    python scripts/workflow_rearchitecture/recovery_guard_2f37ra.py [--update-head]
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

EXPECTED_WORKTREE = "G:/serviceos-phase2f-recovery"
EXPECTED_GITDIR_SUFFIX = "worktrees/serviceos-phase2f-recovery"
EXPECTED_BRANCH = "security/phase-2f-authorization-recovered"
EXPECTED_BASE_ANCESTOR = "4ce23c5"
STATE_FILE = Path(__file__).parent / "recovery_guard_2f37ra_state.json"


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
        failures.append(f"git-dir mismatch: {gitdir!r} does not contain {EXPECTED_GITDIR_SUFFIX!r}")
    if branch != EXPECTED_BRANCH:
        failures.append(f"branch mismatch: {branch!r} != {EXPECTED_BRANCH!r}")

    try:
        merge_base = sh("merge-base", "--is-ancestor", EXPECTED_BASE_ANCESTOR, "HEAD")
    except subprocess.CalledProcessError:
        failures.append(f"{EXPECTED_BASE_ANCESTOR} is not an ancestor of current HEAD")

    state = {}
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())

    expected_head = state.get("expected_head")
    if expected_head is not None and not update_head and head != expected_head:
        failures.append(f"HEAD moved unexpectedly: {head!r} != recorded {expected_head!r}")

    if failures:
        print(json.dumps({"result": "CONCURRENT_WORKTREE_INTERFERENCE", "failures": failures}, indent=2))
        return 1

    STATE_FILE.write_text(json.dumps({"expected_head": head, "branch": branch, "toplevel": toplevel}, indent=2))
    print(json.dumps({"result": "OK", "worktree": toplevel, "branch": branch, "head": head}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
