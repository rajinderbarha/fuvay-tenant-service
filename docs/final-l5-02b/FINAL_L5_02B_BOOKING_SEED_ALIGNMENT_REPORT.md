# FINAL-L5-02B — Canonical Seed Alignment Report

## Evidence-driven conclusion: seed already aligned, re-verified with a fresh rerun this sprint

`scripts/canonical_seed_final_l5_01.py` was rewritten in FINAL-L5-01D to create records in the exact canonical structure (`home_service_booking_drafts` → `service_bookings` → `service_jobs`, matching the real `finalize()` transaction shape field-for-field, though via direct SQL insert rather than calling the service function itself — see note below).

## Real gap found and fixed this sprint: Customer Two had zero seeded bookings
The mission's Part 13 explicitly requires "Customer Two: separate booking for isolation proof." Prior to this sprint, `upsert_job()` hardcoded `cust1` as the booking owner for all 5 seeded jobs — Customer Two (`cust2`, created as a user at line 176) had no booking of their own at all, which only proves *one direction* of isolation (Customer Two sees nothing) rather than genuine bidirectional isolation (Customer Two sees only their own; Customer One cannot see Customer Two's).

**Fix**: `upsert_job()` now accepts an optional `customer` parameter (defaulting to `cust1`, preserving all 5 existing calls unchanged). A 6th job, `L501-JOB-0006` / `L501-BK-0006`, was added for `customer=cust2`.

## Seed run twice this sprint with the fix in place
1st run (after adding the fix): `[CREATE] service_job L501-JOB-0006 (status=new, service_booking=4706ea6d-99af-41ad-94b8-75209ba63def)`, all 5 pre-existing jobs `[SKIP]`.
2nd run (immediately after, no reset in between): **100% `[SKIP]` on every record, including L501-JOB-0006 and the exactly-once-preserved Completed Job Deduction.** `[SUMMARY] {'users': 0, 'tenants': 0, 'pricing_rules': 0, 'coverage': 0, 'jobs': 0, 'ledger': 0, 'notifications': 0}`.

## Row counts before/after the 2nd (idempotency-proving) run
| Table | Before | After | Delta |
|---|---|---|---|
| `service_jobs` | 6 | 6 | **0** |
| `service_bookings` | 6 | 6 | **0** |
| `bookings` | 0 | 0 | 0 |
| `jobs` | 0 | 0 | 0 |

## Required minimums (mission Part 13) — verified present, live
| Requirement | Status |
|---|---|
| Customer One: 1 active/in-progress booking | `L501-BK-0002`/`0003` (`assigned`/`in_progress` service_jobs) |
| Customer One: 1 completed booking | `L501-BK-0004` (`completed`, `collected_amount: 775`) |
| Customer One: 1 cancelled booking | `L501-BK-0005` (`cancelled`) |
| Customer Two: separate booking for isolation proof | **`L501-BK-0006`, fixed this sprint** — live-verified: `GET /v1/customer/bookings` as Customer Two returns exactly `['L501-BK-0006']`; as Customer One returns exactly `['L501-BK-0001'..'0005']` — zero overlap in either direction |

## Note on `home_service_booking_drafts` row count
The table holds 79+ rows, not 6 — the extra rows are `home_service_booking_drafts` genuinely accumulating every started-but-abandoned customer flow across this project's history (expected real behavior) plus 5 created by this sprint's own live API probe script (a real draft-to-match-failure test run, not the seed script). Not a seed-idempotency bug: the seed script's own draft contribution is exactly 1 per seeded job (6 total), each skip-guarded by the same `service_jobs.job_number` check as its paired booking/job.

## Result
**0 duplicate bookings, 0 duplicate projections, 0 duplicate service_jobs, 0 duplicate deductions** — confirmed via a real rerun this sprint, with a genuine new fix (Customer Two's booking) also proven idempotent, not just re-asserting FINAL-L5-01D's unchanged state.
