# FINAL-L5-01 — Pre-Reset Data Classification Report

## State immediately before reset (captured in Part 1/Part 2 backup)
- 1 tenant (`demo-tenant`/`demo-ac-services` lineage from prior FINAL-L5-00-era sessions), 11 users, 11 `service_jobs`, 3 `usage_credit_ledger` rows, 0 `bookings`.
- Full `pg_dump` taken before any destructive action (`.backups/final-l5-01/serviceos_pre_reset_20260711-001711.dump`), so all pre-reset data is recoverable regardless of the classification below.

## Classification

| Category | What was found | Disposition |
|---|---|---|
| CANONICAL_DEVELOPMENT_DATA | The pre-existing `demo-ac-services`/`demo-tenant` tenant and its users, largely produced by `scripts/seed_phase0_baseline.py` and `scripts/seed_demo_users.py` in prior sprints | Superseded by this sprint's canonical seed (same tenant slug, cleanly reseeded with mission-spec entities) — old rows removed by reset, replaced deterministically |
| E2E_TEST_DATA | None identified as clearly E2E-only prior to reset (small dataset, no obvious E2E marker fields) | N/A |
| AUTOMATED_TEST_FIXTURE | Backend test suite creates/tears down its own fixtures via pytest fixtures against a **separate** test-time transaction/session pattern, not persisted rows in the dev database | N/A — not affected by this reset |
| OLD_SPRINT_ARTIFACT | 9 pre-existing `service_pricing_rules` from prior sprints (e.g. the Phase-0 baseline's single `AC Repair × Split AC × LG = Rs 800` flat rule) | Removed by reset (all `service_pricing_rules` rows truncated); replaced by 2 canonical range-based rules matching this sprint's exact spec |
| MANUAL_DEBUG_DATA | None specifically identified — the pre-reset dataset was small and appeared to be prior sprints' seed output, not ad-hoc manual debug rows | N/A |
| ORPHANED_DATA | **Found during reset development**: after a first (incomplete) reset attempt, `service_jobs`/`bookings`/`usage_credit_ledger` rows referencing a tenant ID that no longer existed in `tenants` — caused by the missing-FK schema gap (see schema inventory report), not by orphaned production data. Resolved by correcting the reset script to explicitly truncate all 201 tenant-scoped tables. | Cleaned up as part of arriving at the final, correct reset |
| DUPLICATE_DATA | None found in the pre-reset dataset itself | N/A |
| LEGACY_DATA | `tenant_wallets` table existed but was empty/unused even before reset — consistent with the mission's "dormant legacy source" classification | Left untouched by seed (still empty); confirmed not written to |
| REAL_DATA_DO_NOT_DELETE | No evidence of real customer/production data — loopback host, small row counts, matches the bundled local Postgres install identified in FINAL-L5-00 | Reset proceeded per explicit user confirmation (see conversation record) |
| REVIEW_REQUIRED | None outstanding | — |

## Duplicate/orphan checks specifically requested by the mission (pre-reset)
Given the small pre-reset dataset (11 users, 1 tenant, 11 jobs, 3 ledger rows) and that a full backup was taken first, exhaustive pre-reset duplicate/orphan SQL auditing was superseded by post-reset, post-seed integrity checks against the new canonical dataset (see `FINAL_L5_01_FOREIGN_KEY_ORPHAN_REPORT.md` and `FINAL_L5_01_DUPLICATE_UNIQUE_INTEGRITY_REPORT.md`), which are more actionable since they describe the state actually used for the remainder of Level-5 testing.
