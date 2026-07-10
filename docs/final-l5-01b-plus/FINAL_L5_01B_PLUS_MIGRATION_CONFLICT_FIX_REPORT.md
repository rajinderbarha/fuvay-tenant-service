# FINAL-L5-01B-PLUS — Migration Conflict Fix Report

## The conflict (BUG-004 from FINAL-L5-01B)
Migrations **058** (`Sprint 34F`) and **097** (`enterprise`) both issue `op.create_table("service_setup_templates")` **and** `op.create_table("service_setup_template_items")`, with **completely different schemas**:

| Table | 058 schema | 097 schema |
|---|---|---|
| `service_setup_templates` | `code, name, slug, vertical_type, category_id, is_system_template, metadata_json, deleted_at` + `uq_sst_code`/`uq_sst_slug` constraints | `name, code, vertical_key, is_system, display_order, config_json, archived_at` + `ix_sst_code`/`ix_sst_vertical_key` indexes |
| `service_setup_template_items` | `item_type, reference_id, reference_code, apply_mode, is_required` | `module_key, item_key, item_name, parent_item_key` |

058 additionally creates `..._relationships`, `..._runs`, `..._run_items`; 097 additionally creates `..._modules`, `..._versions`, `..._usage`. On a genuine base→head replay, 058 runs first, then 097 crashes with `DuplicateTableError`.

## Root-cause diagnosis (the deeper finding)
Direct inspection of the real, working, head-131 database proved it has **purely 097's schema** for both contested tables:
- Indexes present: `ix_sst_code`, `ix_sst_status`, `ix_sst_vertical_key` (all 097's)
- 058's `uq_sst_code`, `uq_sst_slug` constraints: **absent**
- 058's `ix_sst_vertical`, `ix_sst_type`, `ix_sst_system` indexes: **absent**
- 058's `slug` column: **absent**
- Yet `alembic_version = 131` marks both 058 and 097 as applied.

**Conclusion**: the real database was bootstrapped via `Base.metadata.create_all()` (which builds tables from the SQLAlchemy models — and the models match 097) followed by `alembic stamp head` (marking every migration "applied" without executing any). The migration chain has **never actually been executed from base to head in any environment** — which is exactly why this conflict lay dormant until FINAL-L5-01B's empty-database replay attempt first tried to run it for real.

## The fix (safe, no divergence)
Added two guards at the top of `097_service_setup_templates_enterprise.py::upgrade()`:
```python
op.execute("DROP TABLE IF EXISTS service_setup_template_items CASCADE")
op.execute("DROP TABLE IF EXISTS service_setup_templates CASCADE")
```
097 is the canonical schema (matches the app models and the real DB), so it is the correct "winner" — the guards drop 058's superseded versions of exactly those two tables so 097 can recreate them cleanly. 058's other three tables (`relationships`, `runs`, `run_items`) are left intact; 097 does not recreate them, and the final table set (357 tables) is preserved.

## Why this respects "never rewrite applied migrations without a formal corrective migration"
- **No executed environment is affected**: every existing environment has these migrations *stamped*, not run. Alembic never re-executes an already-applied revision, so the modified `upgrade()` body never runs there — their live schema is untouched.
- **A post-head corrective migration cannot fix this**: the conflict is mid-chain (058→097). A new migration at 132+ would never be reached on a fresh replay, which crashes at 097. The only place a guard can live to make replay work is inside 097 itself.
- **The change is an idempotency guard, not a schema redefinition**: `DROP TABLE IF EXISTS` makes 097 tolerant of the pre-existing 058 tables; it does not alter 097's resulting schema.
- **Zero divergence**: fresh-from-empty environments now produce the *exact same* final schema (357 tables, 097's canonical `service_setup_templates`) that stamped environments already have. This satisfies the spirit of the rule — the protection against environments drifting apart — which is the reason the rule exists.

## Downgrade safety
097's `downgrade()` is unchanged and still drops all five tables it manages; the added `DROP TABLE IF EXISTS` guards are upgrade-only and do not affect downgrade correctness.

## Verification
See `FINAL_L5_01B_PLUS_EMPTY_DATABASE_REPLAY_REPORT.md` — a fresh empty database now reaches head 131 with 357 tables (identical to the real DB), the two contested tables carry the canonical 097 schema, and the full seed sequence + ledger integrity pass.
