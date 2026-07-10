# Data Cleanup Audit — Phase 0

Real table names differ from the ticket's assumed names (this schema has 344
tables; no `roles`/`permissions`/`role_permissions`/`customers` tables exist
— RBAC is code-based in `app/core/permissions.py`, and "customers" are
`users` rows with `role='customer'`). Real names used below.

## Table counts — before cleanup

| Table | Count | Action |
|---|---|---|
| `users` | 10 | Clean duplicates, preserve canonical |
| `tenants` | 1 (`demo-tenant`, stale placeholder) | Delete + reseed |
| `tenant_service_areas` | 0 | — |
| `customer_addresses` | 0 | — (reseed) |
| `customer_service_credits` | 0 | — |
| `customer_credit_ledger` | 6 (tied to old tenant, but column mismatch found — see blockers) | Attempted delete, see notes |
| `bookings` | 0 | — |
| `jobs` | 0 | — |
| `job_status_history` | 16 (not tenant-scoped; left as-is, no FK to old tenant) | Preserve |
| `payment_records` | 0 | — |
| `customer_reviews` | 0 | — |
| `customer_complaints` | 0 | — |
| `dispute_settlements` | 0 | — |
| `security_deposits` | 1 (old tenant) | Delete |
| `security_deposit_adjustments` | 0 | — |
| `wallet_transactions` | 2 (old tenant) | Delete |
| `tenant_wallets` | 1 (old tenant) | Delete |
| `commission_records` | 0 | — |
| `platform_audit_logs` | 303 | **Preserved** — legitimate audit trail from prior certification sprints, not test-only noise; deleting would violate the append-only audit principle established in the DPDP compliance sprint |
| `service_categories` | 14 | Preserved (config) |
| `service_groups` | 62 | Preserved (config) |
| `master_services` | 60 | Preserved (config) |
| `service_types` | 2 | Preserved (config) |
| `brands` | 35 | Preserved (config) |
| `service_type_mappings` | 2 | Preserved (config) |
| `brand_mappings` | 3 | Preserved (config) |
| `master_issue_types` | 39 | Preserved (config) |
| `master_service_options` | 374 | Preserved (config) |

## Tables that will be cleaned

- `tenants` (only the stale `demo-tenant` row and its dependents)
- `tenant_wallets`, `wallet_transactions`, `security_deposits`,
  `security_deposit_adjustments`, `tenant_package_assignments` — scoped to
  the deleted tenant only
- 5 duplicate/cruft `users` rows (see below)

## Tables that will be preserved

- All catalog config: `service_categories`, `service_groups`,
  `master_services`, `service_types`, `brands`, `*_mappings`,
  `master_issue_types`, `master_service_options` (these were already
  correctly seeded in Phase 1/Phase 2 of this certification and match the
  Phase 0 baseline spec exactly — re-seeding is idempotent, not destructive)
- `platform_audit_logs` (303 rows — legitimate history, not test noise)
- `job_status_history` (16 rows — not tied to the deleted tenant by FK,
  left untouched to avoid orphaning unrelated records)
- Engine registry, platform settings, permission constants — code-based,
  nothing to clean

## Tables that will be re-seeded

- `tenants` (1 new row: Demo AC Services)
- `pricing_tiers`, `tier_locations` (Mid tier, Ludhiana 141001)
- `service_pricing_rules` (AC Repair × Split AC × LG × Ludhiana 141001 = ₹800)
- `service_packages` (Starter Home Services)
- `tenant_package_assignments` (pending_approval, 0 credits until approved)
- `customer_addresses` (Demo Customer, Ludhiana 141001)
- `users.tenant_id` update (link `staff@serviceos.in` to new Demo AC Services tenant)

## Users cleaned (duplicates/cruft)

| Email | Reason |
|---|---|
| `admin@serviceos.io` | Duplicate super_admin account, different domain than canonical `.in` |
| `admin@serviceos.local` | Duplicate super_admin account |
| `staff@serviceos.local` | Duplicate technician account (kept `staff@serviceos.in`) |
| `customer@serviceos.local` | Duplicate customer account (kept `customer@serviceos.in`) |
| `ops.manager.test@serviceos.local` | Unexplained stray `super_admin`-role account from an earlier sprint, no clear purpose |

**Users kept** (canonical, used throughout this certification session):
`admin@serviceos.in` (super_admin), `provider@serviceos.in` (tenant_owner),
`staff@serviceos.in` (technician), `customer@serviceos.in` (customer).

**Correction — `admin@serviceos.local` restored.** Deleting it broke 24
pre-existing integration tests across `tests/test_trust_quality_phase1.py`
and `tests/test_p0_sidebar_duplicate_cleanup.py` that hardcode this exact
email as their auth fixture. Found via the full regression suite run
(`PHASE_0_TEST_RESULTS.md`) — the account was re-created (same role,
`super_admin`, same password `Password123!`) and all 24 tests pass again.
Documented here as the one real mistake this sprint made and fixed, per this
project's standing rule to record both failures and their fixes honestly.

## Foreign key risk notes

- `customer_credit_ledger` delete attempt failed with `UndefinedColumnError:
  column "tenant_id" does not exist` — this table has no direct `tenant_id`
  column (it's keyed by `customer_id`/`user_id` instead). The reset script
  caught this, rolled back that single statement, and continued — no partial
  writes, no orphaned state. The 6 pre-existing rows in this table were **not**
  deleted (they don't reference the removed tenant by any FK the script could
  verify) — documented as a non-blocking gap in
  `PHASE_0_REMAINING_BLOCKERS.md`.
- All deletes were scoped by explicit `tenant_id = :tid` WHERE clauses (never
  a bare `DELETE FROM table` with no filter), and the whole cleanup ran in a
  single SQLAlchemy session with per-statement rollback-on-error to avoid
  transaction poisoning (the same class of bug found and fixed in Phase 1's
  `platform_service.py`).

## Backup/export location

No `pg_dump` backup was taken (user explicitly chose "proceed with full
cleanup" over the backup-first option when asked). This is a local
development database; the deleted rows (1 stale demo tenant + 5 duplicate
users) are trivially re-creatable from the existing seed scripts if needed.
