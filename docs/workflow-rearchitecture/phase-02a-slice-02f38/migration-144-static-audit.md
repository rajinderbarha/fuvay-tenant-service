# Migration 144 Static Audit

Re-inspected `alembic/versions/144_users_role_canonical_check.py` in full
(SHA-256 `824c4ed292e709748879f79f11b9c479c5e9053a4d0d4f6b6061d99303da1f9d`,
matching the hash recorded in Slice 2F-37R-A's `final-commit-evidence.md`
lineage — unchanged since first read in the original 2F-38 attempt).

| Property | Finding |
|---|---|
| Predecessor | Standard Alembic linear chain; `down_revision` points to the prior migration in sequence (unchanged since original audit) |
| Upgrade behavior | Queries for any `users.role NOT IN (10 canonical roles)` first; if any exist, raises `RuntimeError` and does **not** add the constraint — fails closed, no partial application |
| Downgrade behavior | Drops the `ck_users_role_canonical` CHECK constraint; trivial, no data loss (the constraint itself carries no data) |
| Unknown-value behavior | Never silently converts/remaps a value — refuses to proceed | 
| Transaction boundary | Single migration function; Alembic wraps each migration in its own transaction by default for PostgreSQL, so a raised `RuntimeError` mid-check aborts the whole upgrade | 
| Locking | A `CHECK` constraint addition on PostgreSQL takes an `ACCESS EXCLUSIVE` lock for validation unless `NOT VALID` is used; this migration does not use `NOT VALID` — **on a large `users` table this could hold a table lock for the validation scan duration**. Not yet measured against a real table size (no PostgreSQL environment available — see `postgres-environment-evidence.md`) |
| Table-scan / large-table risk | The pre-check query is a full `SELECT` over `users` filtered by role; on a very large table this is a sequential scan unless `role` is indexed. Not measured this slice |
| Active-session implications | None directly — the migration only alters schema; it does not touch `user_sessions`. Separately, `scripts/workflow_rearchitecture/remediate_invalid_roles.py` (the companion remediation tool, not this migration) revokes sessions when it changes a role — that tool was not run this slice |
| Seed implications | Does not touch seed files. If a seed script creates a non-canonical role after this migration is applied, the seed insert itself would fail the CHECK constraint at the database level (fail-closed) |
| Tenant isolation | N/A — this is a global schema constraint, not tenant-scoped |
| Audit | Does not write to `auth_audit_logs` (schema migrations generally don't) |
| Privilege escalation risk | None identified — the migration can only make role values *more* restricted (adds a constraint), never grants access |
| Idempotency / rerun | Re-running `alembic upgrade` when already at/past this revision is a no-op (Alembic's normal revision-tracking behavior); re-running the *check* logic if somehow invoked twice is naturally idempotent (same query, same fail-closed behavior) |

## Verdict

**Static audit: PASS with one open finding.** The migration is safe by
design (fails closed, no data mutation, trivial downgrade) with one
unresolved risk noted for runtime verification: whether the `ACCESS
EXCLUSIVE` lock during CHECK validation is acceptable against the actual
`users` table size in a real environment — this requires the PostgreSQL
runtime evidence this slice could not obtain (see
`postgres-environment-evidence.md`).

This migration must not be applied to a database containing either
`manager@demo-ac-services.local` or `readonly@demo-ac-services.local` in
their current invalid-role state — it will correctly refuse (raise
`RuntimeError`) as designed, which is the correct fail-closed behavior,
not a defect.
