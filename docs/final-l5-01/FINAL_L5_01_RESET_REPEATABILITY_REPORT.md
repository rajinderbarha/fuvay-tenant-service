# FINAL-L5-01 — Reset Repeatability Report

## Method
Full reset → seed → reset → seed cycle executed twice in sequence against the real target database (not a separate throwaway instance, since the empty-DB migration replay path is blocked — see migration chain report). Compared entity data and balances across both cycles.

## Cycle 1 → Cycle 2 comparison

| Metric | Cycle 1 result | Cycle 2 result | Match |
|---|---|---|---|
| Migration head | 131 (head) | 131 (head) | Yes |
| Tenants created | 2 (`demo-ac-services`, `isolation-test-services`) | 2 (same slugs) | Yes |
| Users created | 13 | 13 | Yes |
| Pricing rules | 2 (`final_l5_01_split_ac_lg_141001` 700-850, `final_l5_01_window_ac_lg_141001` 350-500) | 2 (identical codes and ranges) | Yes |
| Jobs | 5 (`L501-JOB-0001..0005`, same statuses) | 5 (identical) | Yes |
| Opening credit balance | 4000 | 4000 | Yes |
| Final credit balance (post-deduction) | 3979.00 | 3979.00 | Yes |
| Deduction amount | -21.00 | -21.00 | Yes |
| Notifications | 4 | 4 | Yes |
| Duplicates introduced | 0 | 0 | Yes |
| Manual SQL repair required | No | No | Yes |

## Assessment
**Full match across both cycles for every canonical business entity and every balance.** No manual SQL repair was needed at any point in either cycle (only iterative script corrections during initial development — see reset execution report — none of which required touching the database by hand; every fix was a script code change followed by a clean reset+seed rerun).

**Result: PASS.**
