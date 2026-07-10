# FINAL-L5-01 — Seed Idempotency Report

## Method
Canonical seed run twice consecutively against the same migrated (post-reset) database, output diffed.

## Run 1 (fresh)
```
[SUMMARY] {'users': 0(*), 'tenants': 2, 'pricing_rules': 2, 'coverage': 1, 'jobs': 5, 'ledger': 1, 'notifications': 4}
```
(* users counter has a script-accounting quirk, see reset execution report; 13 users actually created)

## Run 2 (rerun, same DB, no reset in between)
```
[SUMMARY] {'users': 0, 'tenants': 0, 'pricing_rules': 0, 'coverage': 0, 'jobs': 0, 'ledger': 0, 'notifications': 0}
```
Every single line in run 2's output was `[SKIP]` — including, critically, `[SKIP] Completed Job Deduction for L501-JOB-0004 (already applied, exactly-once preserved)`.

## Verified against required checklist
| Requirement | Result |
|---|---|
| Second run succeeds | Yes, exit 0, no errors |
| No duplicate users | Confirmed — `SELECT email, count(*) FROM users GROUP BY email HAVING count(*)>1` returns 0 rows |
| No duplicate tenants | Confirmed — `SELECT slug, count(*) FROM tenants GROUP BY slug HAVING count(*)>1` returns 0 rows |
| No duplicate tenant memberships | Users are 1:1 with `tenant_id`, no separate membership table used in this schema — not applicable |
| No duplicate services/types/brands | Not re-seeded (reused from existing catalog), so no risk of duplication introduced this sprint |
| No duplicate pricing rules | Confirmed — `rule_code` is the stable lookup key, both rules skip on rerun |
| No duplicate coverage rows | Confirmed — 1 `tenant_service_areas` row before and after rerun |
| No duplicate jobs | Confirmed — 5 `service_jobs` before and after rerun, same `job_number` values |
| No duplicate ledger entries | **Confirmed and most important**: `SELECT job_id, count(*) FROM usage_credit_ledger WHERE event_type='completed_job_deduction' GROUP BY job_id HAVING count(*)>1` returns 0 rows after rerun — exactly-once deduction holds |
| No duplicate notifications | Confirmed — 4 before and after, matched by `(user_id, notification_type, title)` |
| Stable canonical IDs/lookup keys remain stable | Confirmed — tenant `slug`, user `email`, pricing rule `rule_code`, job `job_number` all used as the existence-check key; UUIDs themselves are randomly generated per row but only on first creation, never regenerated on rerun |
| Balances remain unchanged on rerun | Confirmed — `tenant_billing.credit_balance` = `3979.00` both before and after run 2 |

## Row count comparison (before run 2 → after run 2)
`tenants=2→2, users=13→13, service_jobs=5→5, bookings=5→5, usage_credit_ledger=1→1, service_pricing_rules=2→2, in_app_notifications=4→4` — zero drift.

**Result: PASS. Not a blocker.**
