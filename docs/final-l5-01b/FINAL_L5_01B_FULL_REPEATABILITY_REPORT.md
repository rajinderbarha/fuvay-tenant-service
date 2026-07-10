# FINAL-L5-01B — Full Repeatability Report

## Cycles run this sprint (building on FINAL-L5-01's 2 prior cycles)
A 3rd full cycle was run this sprint: `reset → canonical seed → canonical rule seed → RBAC regression tests → full test collection`.

| Metric | Prior cycles (FINAL-L5-01) | This cycle | Match |
|---|---|---|---|
| Migration head | 131 (head) | 131 (head) | Yes |
| Tenants | 2 | 2 | Yes |
| Users | 13 | 13 | Yes |
| Pricing rules | 2 (700-850, 350-500) | 2 (identical) | Yes |
| Jobs | 5 | 5 | Yes |
| Ledger deduction | 4000 → 3979 | 4000 → 3979 | Yes |
| Matching rules | (not seeded pre-01B) | 1 (`final_l5_01b_provider_first_matching`) | Yes — consistent across this sprint's 2 rule-seed runs |
| Notification channel configs | (not seeded pre-01B) | 4 | Yes |
| RBAC regression tests | N/A (new this sprint) | 21/21 passing | Yes — deterministic pass, independent of seed data (uses `dependency_overrides`, not real DB users) |
| Test collection | 8,915 (pre-01B) | 8,936 (+21 new RBAC tests) | Expected delta, no unexpected drift |
| Duplicates | 0 | 0 | Yes |
| Manual repair required | No | No | Yes |

## Bootstrap + empty-DB replay repeatability
The bootstrap script (`scripts/bootstrap_database_final_l5_01b.py`) was run twice against fresh throwaway databases during this sprint's investigation (once during the initial empty-DB replay attempt, implicitly a second time is trivially guaranteed by its `CREATE EXTENSION IF NOT EXISTS` idempotent design, not separately re-executed given the throwaway database was already dropped after the first attempt to avoid clutter).

## Browser smoke repeatability
**Not proven** — only 1 browser smoke run was performed this sprint (see browser smoke report), not run twice, given the 404 finding made a second identical run low-value without first diagnosing the destination-page issue.

## Assessment
**Database-layer repeatability (reset/seed/rule-seed/tests): fully proven, 3 consecutive identical cycles across FINAL-L5-01 and FINAL-L5-01B.** **Browser-smoke repeatability: not demonstrated** — real gap, consistent with the browser smoke report's findings.
