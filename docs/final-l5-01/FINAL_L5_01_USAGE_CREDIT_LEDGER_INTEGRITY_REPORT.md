# FINAL-L5-01 — Usage Credit and Ledger Integrity Report

Canonical active source per mission rule: `tenant_billing.credit_balance`. Confirmed as the only table written to by this sprint's seed for finance state.

| Check | Result |
|---|---|
| Opening credit balance known | Yes — 4000, set at tenant_billing creation |
| Every ledger row has `balance_before` | Yes (1 row, `4000.00`) |
| Every ledger row has `delta` (`credit_delta`) | Yes (`-21.00`) |
| Every ledger row has `balance_after` | Yes (`3979.00`) |
| `balance_before + delta = balance_after` | Confirmed arithmetically: `4000.00 + (-21.00) = 3979.00` ✓ |
| Current `tenant_billing.credit_balance` equals latest ledger `balance_after` | Confirmed: both `3979.00` |
| Completed Job Deduction uses negative delta | Confirmed: `-21.00` |
| Same completed job has at most one deduction row | Confirmed: `SELECT job_id, count(*) ... GROUP BY job_id HAVING count(*)>1` returns 0 rows |
| Rerunning seed does not reapply deduction | Confirmed: run 2 logged `[SKIP] Completed Job Deduction for L501-JOB-0004 (already applied, exactly-once preserved)`; balance unchanged at `3979.00` |
| `tenant_wallets` not used by active finance/bookability logic | Confirmed: the canonical seed never inserts or updates `tenant_wallets`; row count for `tenant_wallets` remains whatever it was pre-sprint (not touched) |

## Repeatability confirmation
A full reset → seed → reset → seed cycle was executed twice this sprint (see `FINAL_L5_01_RESET_REPEATABILITY_REPORT.md`). Both times, the opening balance (4000) and final balance after the single completed-job deduction (3979) were identical.

**Result: PASS. Not a blocker. Exactly-once deduction proven, active balance source correctly isolated to `tenant_billing`, `tenant_wallets` confirmed dormant.**
