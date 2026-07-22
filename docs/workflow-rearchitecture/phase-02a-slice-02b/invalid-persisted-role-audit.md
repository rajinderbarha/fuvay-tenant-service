# Invalid Persisted Role Audit

**Method:** read-only SQL queries against the repo's configured development database (`DATABASE_URL` in `.env`: `postgresql+asyncpg://serviceos:serviceos@127.0.0.1:5432/serviceos`), via a throwaway Python script using SQLAlchemy's async engine. No `UPDATE`/`DELETE`/`INSERT` statement was issued at any point. This is the only slice in this workflow-rearchitecture series that queried a live database rather than reasoning from source code alone.

## Query 1 — role distribution across all users

```sql
SELECT role, count(*) FROM users GROUP BY role ORDER BY role;
```

| role | count |
|---|---|
| admin_finance | 1 |
| admin_operations | 1 |
| admin_readonly | 1 |
| admin_security | 1 |
| customer | 4 |
| staff | 1 |
| super_admin | 3 |
| technician | 5 |
| **tenant_manager** | **1** |
| tenant_owner | 6 |
| **tenant_readonly** | **1** |

**Two invalid values found:** `tenant_manager` and `tenant_readonly` — neither exists in `app/core/permissions.py::ROLE_PERMISSIONS`. Every other value is one of the 10 canonical roles.

## Query 2 — detail on the 2 invalid accounts

```sql
SELECT id, email, role, tenant_id, is_active, is_verified, created_at
FROM users WHERE role IN ('tenant_manager','tenant_readonly','tenant_finance','tenant_support','tenant_staff_admin','platform_admin');
```

| id | email | role | tenant_id | is_active | is_verified | created_at |
|---|---|---|---|---|---|---|
| 72640932-ef3c-4ce5-92a1-6609bff35ee0 | manager@demo-ac-services.local | tenant_manager | 5209ef33-... | true | true | 2026-07-11 05:02:53 UTC |
| 05deaee8-03f2-40f9-8af6-2f21892c075f | readonly@demo-ac-services.local | tenant_readonly | 5209ef33-... | true | true | 2026-07-11 05:02:53 UTC |

Both belong to tenant `5209ef33-a53e-4fc0-b3f6-006335b8d712`, slug `demo-ac-services` (confirmed via a third query). Both are `is_active=True` and `is_verified=True` — **live, usable-looking accounts**, though functionally they can authenticate but every subsequent permission check (`PermissionChecker.has()`) will deny them everything, since neither role string exists in `ROLE_PERMISSIONS`.

## Query 3 — blast radius

```sql
SELECT count(*) FROM staff_permissions WHERE user_id IN (<the 2 ids>);  -- 0
SELECT count(*) FROM tenants;  -- 4 (total, this database)
```

- 0 `StaffPermission` override rows exist for either account (no per-user override complexity to consider in remediation).
- Only 4 tenants exist in this database total — this is a small development/demo environment, not a large multi-tenant production dataset.

## Source of the invalid values

`scripts/canonical_seed_final_l5_01.py` lines 149-153:
```python
manager = await get_or_create_user(db, "manager@demo-ac-services.local", "Tenant Manager",
                                    "tenant_manager", tenant_id=tenant_id)
readonly = await get_or_create_user(db, "readonly@demo-ac-services.local", "Tenant Read Only",
                                     "tenant_readonly", tenant_id=tenant_id)
```

This script writes directly via its own `get_or_create_user()` helper (raw SQL/ORM insert), **bypassing** `app/engines/tenant_engine/admin_service.py::create_user`'s `VALID_TENANT_ROLES` check entirely — so Slice 2's fix to that validation set does not, and could not, have prevented this seed script from creating these rows (it never went through that API).

## A related bug was already found and fixed by a prior engineer

The same seed script also created 3 demo "admin" accounts (`admin.ops@serviceos.local`, `admin.finance@serviceos.local`, `admin.readonly@serviceos.local`) with `role="super_admin"` and only a `platform_role` label ("operations"/"finance"/"read_only") to distinguish intent — since `platform_role` is confirmed advisory/unenforced (Phase 1A finding), these 3 accounts were fully-privileged `super_admin` despite their names.

`scripts/seed_admin_roles_final_l5_05l.py` exists specifically to repoint these 3 accounts' `role` column to the real least-privilege roles, and — per Query 1 above — **this remediation has already been applied**: exactly 1 row each for `admin_operations`/`admin_finance`/`admin_readonly`, and `super_admin` shows 3 (not 6), confirming these 3 accounts were corrected and the "extra" 3 super_admin count comes from elsewhere (likely the real platform super admin plus 2 others, not re-investigated further this slice).

**No equivalent remediation script exists for the 2 `tenant_manager`/`tenant_readonly` accounts.** See `invalid-role-remediation-recommendation.md`.

## Other tables checked

- No dedicated invitation/membership table exists in this schema (`information_schema.tables` query for `%invit%` returned zero results) — invitations in this codebase are modeled as `User` rows created with `force_password_change=True`, not separate pending-invite records. The 2 rows above are the complete picture; there is no separate "pending invitation" state to also check.

## Verification level
RUNTIME_VERIFIED — all findings above are from direct, live queries against the actual configured database, not inferred from source code.
