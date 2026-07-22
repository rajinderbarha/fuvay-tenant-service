# Database Integrity Guard

## Investigation

| Item | Finding | Verification |
|---|---|---|
| Column type | `users.role` is `VARCHAR(30)`, no enum type | RUNTIME_VERIFIED (`information_schema.columns`) |
| Enum constraint | None | RUNTIME_VERIFIED |
| Check constraint | None — `pg_constraint` for the `users` table showed only the primary key | RUNTIME_VERIFIED |
| Foreign keys on role | None (role is not itself an FK; there is no `roles` table anywhere in the schema) | RUNTIME_VERIFIED |
| Application-level validation | Present but split: `VALID_TENANT_ROLES` (tenant_engine), `VALID_PLATFORM_ROLES` (auth/service.py), no single unified validator | RUNTIME_VERIFIED |
| Historical migrations | 143 prior migrations exist; none previously added a constraint on `users.role` | SOURCE_VERIFIED (grepped for "role" across alembic/versions, found no prior CHECK/enum on this column) |
| Multi-role or membership models | None — `role` is a single scalar column per user, no many-to-many role/membership table exists | RUNTIME_VERIFIED |
| Compatibility concerns | The column is shared by all account types (platform admins, tenant owners, staff, technicians, customers) — a single flat namespace, confirmed by the live role-distribution query showing all 10 canonical values plus the 2 invalid legacy ones coexisting in the same column | RUNTIME_VERIFIED |

## Decision: implement a DB-level CHECK constraint

Unlike the other role-sounding fields found and correctly left alone in Slices 2B/2C (`NotificationTemplate.audience`, `ServiceChecklistItem.owner_role`, `ComplianceRequest.subject_type`, `IntelligenceKnowledgeBase.allowed_roles_json`), `users.role` **is** the literal RBAC-enforcement field — the one column `PermissionChecker` actually reads. There is no legitimate architecture reason for this column to ever hold a value outside the 10 canonical roles; every application-level validator that touches it already agrees on that (they just don't share one implementation). A DB-level guard here does not risk breaking a different, legitimate use case, because none exists.

## Implementation

`alembic/versions/144_users_role_canonical_check.py`:
1. **Detects invalid existing records first** — runs a `SELECT` for any `role NOT IN (<10 canonical values>)` before attempting the constraint.
2. **Fails clearly if any are found** — raises `RuntimeError` naming every offending account's email and role, with an explicit pointer to the remediation script and this slice's documentation. Does not proceed to add the constraint.
3. **Never silently rewrites data** — no `UPDATE` statement exists anywhere in this migration.
4. **Reversible** — `downgrade()` drops the constraint.

## Proof it works (run live this slice)
```
$ alembic upgrade head
...
RuntimeError: Migration 144 aborted: users.role contains values outside the 10
canonical RBAC roles: 'manager@demo-ac-services.local'='tenant_manager',
'readonly@demo-ac-services.local'='tenant_readonly'. Remediate these accounts
first ...
```
Confirmed via `alembic current` (unchanged at revision 143) and a follow-up role-distribution query (byte-for-byte identical to before the attempt) that no schema change and no data change occurred.

## Migration tests
`tests/test_phase2c_role_integrity.py::TestMigration144DetectionLogic` — 2 tests:
1. Proves the detection query correctly finds a freshly-inserted invalid-role row (inserted and rolled back within the test itself, using an existing real tenant as the FK target — never touches the 2 known real invalid accounts or commits any change).
2. Proves the detection query never flags a canonical role as invalid, against the real current data.

Both tests open their own database engine (matching the existing precedent in `tests/test_final_l5_05k_topup_migration.py`), rather than mocking, because the goal is to prove real SQL behavior against the real column, not mocked behavior.

## Status
Built, tested, proven correct — **not yet applied** to the database, because it cannot be until the 2 known accounts are remediated (by design). This is the intended, safe state: the guard exists and will apply cleanly the moment remediation happens, rather than either being blocked from ever being written, or being forced through by weakening its detection logic.
