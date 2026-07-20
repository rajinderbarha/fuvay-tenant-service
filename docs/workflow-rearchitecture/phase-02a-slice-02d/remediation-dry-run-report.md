# Remediation Dry-Run Report — Slice 2D

All runs executed live against the real database this slice, using the extended `remediate_invalid_roles.py` (v2, `slice-2d-v2`).

## Run 1 — default dry-run (no arguments)
Result: reports both accounts as `unmapped_invalid_accounts`, zero changes. Baseline confirmation before any targeted action.

## Run 2 — targeted dry-run for manager@ remediation
```
python scripts/workflow_rearchitecture/remediate_invalid_roles.py \
  --mapping 72640932-ef3c-4ce5-92a1-6609bff35ee0=staff \
  --disable 72640932-ef3c-4ce5-92a1-6609bff35ee0 \
  --allow 72640932-ef3c-4ce5-92a1-6609bff35ee0 \
  --reason "Slice 2D: zero usage/evidence demo account; disabling rather than granting unproven manager-shaped access"
```
Result: `changes` shows exactly the intended single change (`previous_role: tenant_manager`, `new_role: staff`, `disable: true`), `unmapped_invalid_accounts: []` (correctly scoped away from `readonly@` via `--allow`), `errors: []`. This dry-run output was reviewed before proceeding to apply, per Workstream 7's required sequence.

## Effective-permission comparison performed before apply
Per Workstream 7 step 2 ("compare effective permissions"): before applying, confirmed via `permission_checker.has()` inspection that `staff` combined with `is_active=false` results in the account being unable to authenticate at all (login checks `is_active` before any permission check is reached — SOURCE_INFERRED from standard login-flow patterns in this codebase, not independently re-traced line-by-line this slice) — i.e. the "effective permission" after remediation is "none, because the account cannot log in," which is a safe, deliberate outcome for a disabled demo account.

## Session impact confirmed before apply
0 sessions existed for this account — confirmed via the same live query used in Slice 2C's audit, re-run immediately before the apply step. Nothing to revoke.

## Database constraint readiness confirmed before apply
Migration 144 (not yet applied) would, after this account's remediation, name only the remaining `readonly@` account — confirmed by re-running the migration's detection query logic manually (not the migration itself) against the post-apply state, before actually running `alembic upgrade head` (which was then run afterward and confirmed this exact narrowing — see `database-constraint-report.md`).

## No dry-run was generated for a readonly@ mapping
Because no safe target role exists for this account (`tenant-readonly-decision.md`), no dry-run preview was produced for it — doing so would imply a candidate mapping is under active consideration, which it is not, pending the product decision described in `affected-account-final-disposition.md`.
