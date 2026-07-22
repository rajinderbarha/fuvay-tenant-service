# Targeted Test Report

`python scripts/workflow_rearchitecture/verify_2f37.py` (the closest
existing targeted verifier covering role registry, permission registry,
access scopes, StaffPermission-adjacent checks, cross-tenant ownership,
M01/geo/2F-35/2F-36/2F-37 non-regression, and N01 non-regression in one
run): **21/21 PASS**, re-run twice this slice (once immediately after
worktree creation, once again after the checkpoint commit), identical
both times.

A dedicated `verify_2f38.py` was not built this slice as a from-scratch
new tool — see `slice-2f38-verifier-spec.md` /
`slice-2f38-verification-report.md` for what this slice certifies using
the existing tool plus the manual/documented findings above, and what a
true Slice-2F-38-specific verifier would still need to add.
