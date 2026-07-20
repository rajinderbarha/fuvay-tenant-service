# Recovery Strategy Decision — Strategy B (Consolidated)

## Decision

**Strategy B — consolidated recovery.** Exact per-slice (2F-34/35/36/37)
implementation commit boundaries could not be credibly reconstructed.

## Why Strategy A was rejected

Every file under `app/`, `alembic/`, and `scripts/workflow_rearchitecture/`
touched by this program existed, at every point in this repository's actual
git history, in exactly one state: uncommitted working-tree content on top
of `4ce23c5`. There is no earlier commit, stash, reflog entry, or tag that
captures "the state right after 2F-35 was applied but before 2F-36 began" —
that intermediate state was never persisted anywhere git can recover it
from. The only evidence for per-slice boundaries is:

- Filename markers (e.g. `test_phase2f36_enterprise_tenant_admin_operational_batch.py`,
  `verify_2f37.py`) — reliable for *labeling* which slice a given new file
  belongs to, but say nothing about which lines of a *shared, multiply-edited*
  file like `app/core/permissions.py` or `app/dependencies/auth.py` were
  changed by 2F-35 versus 2F-36 versus 2F-37.
- Prose in the (also uncommitted) documentation tree — narrative, not
  git-verifiable.

Constructing synthetic sequential commits by manually splitting each
multiply-edited file's diff into "the part that must be 2F-35" versus
"the part that must be 2F-36" would require re-deriving, by inspection, a
boundary that the original slices themselves never recorded — indistinguishable
from fabrication. Slice 2F-37R's own mission text prohibits exactly this:
"Do not fabricate per-slice commits to make history look cleaner."

## Why Strategy B is sound anyway

Strategy B does not require trusting the file-path classification for
correctness — it requires the **final state** to be independently
verifiable, which this slice did:

- `changed-path-classification.csv`: all 3,001 changed paths classified,
  0 UNKNOWN, cross-checked against actual application behavior (the
  `my_work_router`/`my_work_service` misclassification was caught exactly
  because `app/main.py` failed to import when they were excluded — see
  `unknown-path-resolution.md`).
- `verify_2f37.py`: 21/21 PASS against the actual reconstructed, committed
  tree — including R13 (313/313 canonical arithmetic), R14 (0 unprotected),
  R19/R20 (canonical and matrix hashes match the frozen post-2F-37 values).
- Full `tests/test_phase2f*.py` regression (see `phase2f-regression-report.md`).

The consolidated commit's correctness rests on these independent,
reproducible checks against the actual code — not on the classification
labels being historically precise.

## What this means for Slice 2F-38

Slice 2F-38, if restarted from `security/phase-2f-authorization-recovered`,
must not claim to certify "Slice 2F-35's routes" versus "Slice 2F-37's
routes" as separately-verified historical checkpoints — only the final,
combined 313/313 state is certifiable from this recovery. Any claim
requiring proof of an intermediate historical state (e.g. "2F-35 alone
reached 252/273") should cite the pre-existing 2F-35 documentation as a
*narrative* record, explicitly caveated as unverifiable from git history.
