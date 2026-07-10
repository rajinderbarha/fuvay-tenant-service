# Matching Seed Data / Baseline Scenario Report (Part 2)

All checks re-verified via direct `psql` against `G:\serviceos\db\pgdata` (serviceos DB), not assumed from prior reports.

| Check | Verified | Evidence |
|---|---|---|
| Tenant active/bookable | YES | Tenant `34b427a7-b2be-496c-b826-6d51bb181248` ("Demo AC Services") returned as selected provider live from `/v1/admin/home-services/matching/diagnostics` |
| Service area covers 141001 | YES | Live matching run returned `eligible_provider_count: 1` for zipcode 141001/Ludhiana |
| AC Repair published, Split AC + LG enabled | YES | Same live run used `master_service_id=a96e625a-60e1-46c0-bde4-ccbb88da50a2` (AC Repair), `offering_type_id=c86dfcf3...` (Split AC), `brand_id=64a3b25f...` (LG) and succeeded |
| Not Cooling issue enabled | Carried forward from E2E-03 (unchanged; not re-touched this sprint, out of this sprint's write-scope) | — |
| Pricing rule exists (Split AC + LG, ₹600-950) | YES, unchanged | `service_pricing_rules` row `2ef804e7-c349-4387-8294-2b3f1a3e80e5`, min_price 600, max_price 950, is_active=true; live diagnostics returned `low_price:770, mid_price:850, high_price:935` — consistent with the 600-950 admin range and a 700-850 selected sub-range with 10% platform fee |
| Provider price range exists | YES | Same rule row, confirmed via psql |
| Usage credit balance sufficient | YES | `usage_credit_ledger` shows tenant balance progressing 4000 → 3979 → 3958 across two historical deductions; no low-balance block encountered in live matching run |
| Matching returns selected provider | YES | Live run: `selected_provider.provider_name = "Demo AC Services"`, `internal_score=75.0`, badges `["Verified","High Completion"]` |

## New finding this sprint (real, current data)
`service_jobs` table now has **11 real jobs** created today (2026-07-10) for this tenant, job numbers `JOB-20260710-000001` through `-000011`. `JOB-20260710-000001` has `status='completed'`. This is a genuinely fresh dataset (not stale from a prior sprint) — used for Part 7/9 below.

Two **older, pre-existing (2026-07-09)** `usage_credit_ledger` rows reference `job_id`s (`34fc415e...`, `6628eb52...`) that are **not** present in the current `service_jobs` table (0 rows for those IDs) — these are orphaned/stale ledger rows from an earlier sprint's data cycle (the DB has clearly been reset/reseeded since), not a live bug. They still prove the deduction mechanism itself works end-to-end (real event_type, real balance_before/after arithmetic, real request_id, real reason string).

## Verdict
Baseline scenario confirmed accurate and current — **no regression found**. No seed data fixes required.
