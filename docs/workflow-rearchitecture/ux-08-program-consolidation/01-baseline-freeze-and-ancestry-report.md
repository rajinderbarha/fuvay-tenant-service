# UX-08 Workstream 1: Baseline Freeze + Ancestry Verification

Status: FRESH-VERIFIED THIS PASS (commands run directly in the UX-08 worktree,
output captured verbatim below).

## Worktree / branch

- Path: `G:/serviceos-ux08-program-consolidation`
- Branch: `design/ux-08-program-consolidation`
- Created from: `50fe95b` (UX-07 final commit, branch
  `design/ux-07-cross-app-production-readiness`)
- Command used:
  ```
  git worktree add G:/serviceos-ux08-program-consolidation -b design/ux-08-program-consolidation 50fe95b
  ```
- Note on execution: the initial `git worktree add` invocation hit the tool's
  2-minute command timeout partway through the file checkout (a large repo
  checkout on this Windows filesystem occasionally exceeds 2 minutes). This
  left `.git/worktrees/serviceos-ux08-program-consolidation/index.lock`
  behind and the working tree showing ~4574 files as staged-deleted. This was
  NOT tooling-file drift (no `app.json`/`package.json` values had changed) and
  NOT concurrent-worktree interference (no other process touched this
  worktree) — it was a straightforward interrupted first-time checkout.
  Resolved by removing the stale `index.lock` and running
  `git checkout HEAD -- .`, after which `git status` reported "nothing to
  commit, working tree clean" and `git log --oneline -1` confirmed HEAD =
  `50fe95b`. Documented here in the interest of full honesty about the setup
  process, not because it reflects a defect in any commit.

## Ancestry verification of the four prior UX baselines

Per the brief, verified whether the previously approved UX baselines are all
ancestors of the UX-08 starting point, `50fe95b`.

Commands run (from `G:/serviceos-ux08-program-consolidation`), exit codes
captured immediately after each (`0` = confirmed ancestor):

```
$ git merge-base --is-ancestor 7488335 50fe95b; echo "exit=$?"
exit=0

$ git merge-base --is-ancestor 493a132 50fe95b; echo "exit=$?"
exit=0

$ git merge-base --is-ancestor b426e08 50fe95b; echo "exit=$?"
exit=0

$ git merge-base --is-ancestor 50fe95b 50fe95b; echo "exit=$?"
exit=0
```

**Result: all four commits — `7488335` (UX-04 final), `493a132` (UX-05
final), `b426e08` (UX-06 final), and `50fe95b` itself (UX-07 final) — are
confirmed ancestors of `50fe95b`. No conflict. Proceeding with
consolidation, not stopping for `UX08_BASELINE_CONFLICT`.**

## How this ancestry came to be (reconciled against prior evidence)

This matches exactly what
`docs/workflow-rearchitecture/ux-07-cross-app-production-readiness/branch-worktree-baseline.md`
(written during UX-07 Round 1, prior to any UX-08 work, cited verbatim here
rather than re-derived) documented at the time:

1. The three approved baselines (`7488335`/UX-04, `493a132`/UX-05,
   `b426e08`/UX-06) did **not** originally sit on one ancestry chain.
   `b426e08` (UX-06 Customer App) was branched from plain `master`
   (`50840ac`) and never incorporated the UX-04/UX-04B/UX-05 lineage.
   `493a132` (UX-05 closure) already contained `7488335` (UX-04B) as an
   ancestor (UX-05 was branched forward from the UX-04B baseline).
2. UX-07's worktree (`G:/serviceos-ux07-cross-app`) was created from
   `design/ux-05b-finalization` @ `493a132` (deepest existing chain: UX-04B +
   UX-05).
3. UX-07 then merged `b426e08` (UX-06 final) into that branch at commit
   `5461f6c` — confirmed via
   `git log -1 --format="%H %P" 50fe95b` → `50fe95bd... fcb987bf...` (a
   single-parent commit, i.e. `50fe95b` is a normal descendant commit after
   the merge, not the merge commit itself) and
   `git log --merges --oneline b426e08..50fe95b` → returns exactly one merge
   commit, `5461f6c UX-07: integrate approved UX-06 Customer App baseline
   (b426e08) onto UX-04+UX-05 baseline (493a132) -- disjoint file sets
   confirmed, zero conflicts`.
4. `git log --oneline --graph` from `50fe95b` confirms the full UX-07 Pass
   1-3f commit sequence sits linearly on top of that merge, terminating at
   `50fe95b` ("UX-07 Pass 3f: docs -- accessibility audit CSV, remediation
   report, Playwright evidence report, screenshots, status rationale/approval
   gate, known-limitations + verification-report appendices").

This independently reproduces (rather than blindly trusts) the UX-07-era
documented merge, and confirms the ancestry chain is still intact four
rounds later. No new merge was needed for UX-08 — the ancestry requirement
was already satisfied by inheriting from `50fe95b` directly.

## Worktrees / branches explicitly NOT touched this pass

Confirmed via `git worktree list` at the start of this pass (see full output
in the session transcript) — the following pre-existing worktrees were left
untouched:

- `G:/serviceos` (main tree)
- `G:/serviceos-bargain-optional-fix`
- `G:/serviceos-phase2f-recovery`, `-phase2f38-certification`,
  `-phase2f39-remediation`, `-phase2f39a-route-census`,
  `-phase2f39a2-route-census`, `-phase2f39a2r-remediation`,
  `-phase2f39a3-route-census`, `-phase2f39a4-product-decision`,
  `-phase2f39a5-final-decisions`, `-phase2f39b-migration144`,
  `-phase2f39c-suite-stability`
- `G:/serviceos-ux05b-finalization`
- `G:/serviceos-ux06-customer-app`
- `G:/serviceos-ux07-cross-app`
- `G:/serviceos/.claude/worktrees/agent-ab43bbb80d9715b62`

Only `G:/serviceos-ux08-program-consolidation` (this worktree) was created
or modified.
