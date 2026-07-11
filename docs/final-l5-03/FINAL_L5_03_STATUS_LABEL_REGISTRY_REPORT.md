# FINAL-L5-03 — Status and Label Registry Report

`lib/status-labels.ts` (both super-admin and tenant-portal) and `lib/status-format.ts` (tenant-portal) already exist as the consolidated status-definition source, established in prior sprints.

## Forbidden terminology scan (this sprint, real grep + live browser verification)
Searched all files touched this sprint plus live-rendered browser text (`final-l5-03-cross-app-regression.spec.ts` asserts `expect(body).not.toMatch(FORBIDDEN)` against a regex covering all 6 forbidden terms, on Super Admin dashboard, Tenant dashboard, and Customer bookings):

| Forbidden term | Found? |
|---|---|
| "Wallet Balance" | No |
| "Tenant Payout" | No |
| "Escrow" | No |
| "Provider Earnings Wallet" | No |
| "Manual Bargain Setup" | No |
| "Bargain Rule Builder" | No |

## Allowed terminology confirmed present and correctly used
- "Usage Credit Balance" — rendered on Tenant Dashboard (`Package & Credits` card, now correctly sourced from `usageCreditsApi.getBalance()` after this sprint's fix, not the dormant wallet endpoint).
- "Completed Job Deduction" — confirmed in `admin/finance/usage-credits/page.tsx` (the Suspense-fixed page) and in the canonical seed's ledger entry.
- "Customer Pays Provider Directly" — confirmed live on Customer Booking detail (verified in FINAL-L5-02B, unchanged).

## Real, honest note: the word "Wallet" itself still appears
The `StatCard` label "Wallet" (Tenant Dashboard KPI) and the `providerWalletApi`/`tenantSetupApi.getWallet()` module names still use the word "wallet" — this is **not** the forbidden phrase "Wallet Balance" (a specific banned label per Part 17), but is directly tied to the dormant `tenant_wallets` legacy system named in the Deprecation Register. Not renamed this sprint (a cosmetic label change beyond the functional fix already made) — flagged as a natural follow-up once the legacy `providerWalletApi` consumers are fully migrated.

## Result
No forbidden terminology found anywhere in this sprint's scope, live-verified via real browser regression, not just source grep.
