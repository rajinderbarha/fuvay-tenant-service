# E2E-11 Finance Routes Report

## Routes Found

| Route | File | API Called |
|-------|------|-----------|
| `/finance` | `app/(tenant)/finance/page.tsx` | redirect → `/finance/package` |
| `/finance/package` | `app/(tenant)/finance/package/page.tsx` | `tenantSetupApi.getPackage()`, `usageCreditsApi.getBalance()` |
| `/finance/usage-credit-ledger` | `app/(tenant)/finance/usage-credit-ledger/page.tsx` | `usageCreditsApi.getBalance()`, `usageCreditsApi.getLedger()` |
| `/finance/security-deposit` | `app/(tenant)/finance/security-deposit/page.tsx` | `tenantSetupApi.getWallet()` |
| `/account/credits` | `app/(tenant)/account/credits/page.tsx` | (separate credits view) |

## Notes

- `/finance` cleanly redirects to `/finance/package` (no legacy wallet/payout content).
- `/finance/package` was fixed (E2E-11) to use `usageCreditsApi.getBalance()` instead of the stale `tenantSetupApi.getWallet()` call.
- `/finance/usage-credit-ledger` was previously fixed (HS9B) from wallet endpoint to real usage credit endpoints.
- `/finance/security-deposit` uses `tenantSetupApi.getWallet()` to read the `security_deposit` sub-key — correct usage (not financial wallet balance).

## Status: PASS
