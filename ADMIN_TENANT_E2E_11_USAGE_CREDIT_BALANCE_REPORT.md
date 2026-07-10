# ADMIN-TENANT-E2E-11 — Usage Credit Balance Report

## Checks
1. Visible — confirmed on `/finance/package` and `/finance/usage-credit-ledger`.
2. Matches backend/DB — confirmed: `GET /v1/provider/usage-credits/balance`
   → `usage_credit_balance: 3937.0`, matching the real ledger chain
   (`4000 → 3979 → 3958 → 3937`, the last hop produced live in the prior
   E2E-04B session by completing `JOB-20260710-000002`).
3. Not hardcoded — confirmed, sourced from `useApi(() => usageCreditsApi.getBalance())`,
   no literal fallback values in the render path besides `safeNum()`'s
   `0` guard for genuinely missing data.
4. Refreshes after ledger changes — not re-tested with a new live
   completion this pass (would duplicate E2E-04B's already-verified
   exactly-once completion flow); the balance's correctness after the
   most recent real completion was confirmed via direct API cross-check.
5. Currency/unit label clear — "credits available" / "Usage Credit
   Balance" labels used consistently, no ambiguous currency symbol on
   the credit figure itself.
6. Does not say "Wallet Balance" — confirmed via forbidden-label scan.

## Verdict
Full pass. Real, correct, matching balance across both pages that show
it.
