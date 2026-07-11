# FINAL-L5-03 — API Module Organization

Both `super-admin/lib/api.ts` and `tenant-portal/lib/api.ts` already organize exports by domain (not by page) — confirmed by direct reading this sprint. Representative domain modules found:

**super-admin**: `authApi`, `platformUsersApi`, `tenantApi`, `enterpriseApi` (export/saved-views), plus dozens more per-domain objects (finance, marketing, catalog, etc. — not exhaustively re-listed here since FINAL-L5-02 already inventoried the full backend endpoint surface).

**tenant-portal**: `authApi`, `serviceJobsApi`, `serviceJobAssignmentApi`, `usageCreditsApi`, `providerWalletApi` (legacy, see Deprecation Register), `tenantSetupApi`, `categoryDashboardApi`, `myStatusApi`, `providerOfferingsApi`, `financeApi`, and more.

**customer-app**: `frontend/customer-app/lib/api/customer-home-services.ts` — already domain-scoped (booking-drafts, bookings, catalog), with explicit source-file comments mapping each function to its real backend router (established in FINAL-L5-02B).

## Rules verified
1. **Page components must not assemble raw endpoint URLs** — verified true except the 5 super-admin pages + 1 tenant-portal login page fixed this sprint (see API Client Migration Report).
2. **Response types match real backend contracts** — spot-verified this sprint via live API calls (usage-credits balance, provider jobs, customer bookings all match their TS interfaces).
3. **Deprecated endpoints marked** — `providerWalletApi`/`tenantSetupApi.getWallet()` (both call the dormant `/v1/provider/wallet`) are now marked in the Deprecation Register; source comments added at the one active call site fixed this sprint.
4. **Canonical endpoints documented** — this sprint's fixes each carry an inline comment naming the canonical replacement and why.
5. **Legacy endpoints don't silently remain primary** — `providerWalletApi`/`tenantSetupApi.getWallet()` had exactly one primary consumer (`TenantLayout.tsx`, fired on every page load) — fixed to use `usageCreditsApi.getBalance()`. `providerWalletApi` itself is still exported (3 other, less-critical consumers — `finance/package`, `finance/security-deposit`, `provider/wallet` pages — not migrated this sprint, see Deprecation Register) but is no longer the *dashboard-wide, every-page* dependency it was.
6. **Domain modules contain no UI code** — confirmed, `lib/api.ts` files are pure TypeScript functions/types, zero JSX.

## Result
Domain organization already conforms to the mission's target; this sprint's real contribution was closing the raw-URL-assembly gaps found.
