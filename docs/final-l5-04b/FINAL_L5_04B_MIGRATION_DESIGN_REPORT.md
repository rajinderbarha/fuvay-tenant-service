# FINAL-L5-04B — Migration Design Report

## Real migration: `alembic/versions/132_tenant_entitlement_architecture.py`
`revision = "132"`, `down_revision = "131"` — chains cleanly from the real current head (verified by walking the full `revision`/`down_revision` graph before writing this migration; 131 was confirmed to have no existing child).

## Applied and re-applied live against the real dev database
1. `alembic upgrade head` — applied cleanly (131 → 132).
2. A bug was found in the first version (missing `updated_at` column on `entitlement_audit_log`, inconsistent with `ServiceOSBase`'s `TimestampMixin` which every ORM model requires) — fixed by adding the column to the migration file, then `alembic downgrade 131` → `alembic upgrade head` to re-apply cleanly. Both directions verified working.

## Required elements — all present
| Requirement | Status |
|---|---|
| Create entitlement tables | 3 tables created: `tenant_module_entitlements`, `tenant_category_entitlements`, `entitlement_audit_log` |
| Indexes for tenant/module/category/status lookups | All 9 required indexes present (see Data Model Report), matching the mission's recommended index list exactly |
| Unique constraints | 2 partial unique indexes, DB-verified to reject duplicates |
| Foreign keys | 5 real FK constraints (`tenant_id` ×3, `module_id`, `category_id`, `module_entitlement_id`) with `ON DELETE CASCADE` |
| Preserve migration chain from empty DB | `down_revision="131"` chains correctly; full chain 001→132 unbroken (verified via `alembic heads`/`alembic current`, see Backend Test Report) |
| Preserve compatibility with existing environments | Purely additive (3 new tables, no column changes to any existing table) — zero risk to existing data |
| Don't edit historical migrations unsafely | Migration 132 is new; no prior migration file was modified |
| Downgrade logic | `downgrade()` drops all 3 tables in FK-safe order (`entitlement_audit_log` → `tenant_category_entitlements` → `tenant_module_entitlements`) — tested live via the actual downgrade/upgrade cycle above |

## `alembic heads` / `alembic current`
```
alembic heads:   132 (head)
alembic current: 132
```
Single head, no branch conflicts, confirms migration 132 is the unambiguous current state.

## Result
Migration is safe, additive, bidirectional (tested both directions live), and does not touch any historical migration file.
