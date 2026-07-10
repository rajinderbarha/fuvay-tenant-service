# ADMIN-TENANT-E2E-11 — Routes Report

| Ticket route | Actual route | Status | Real API | Data | Notes |
|---|---|---|---|---|---|
| `/tenant/finance` | `/finance` | 200, **redirects** to `/finance/package` | n/a (redirect) | n/a | **Fixed this pass** — previously rendered a legacy Wallet/Payout page violating this ticket's forbidden-label rules; now redirects to the real canonical page |
| `/tenant/finance/usage-credits` | `/finance/package` | 200 | `tenantSetupApi.getPackage()`, `getWallet()` | real package + balance | canonical finance overview |
| `/tenant/finance/usage-credit-ledger` | `/finance/usage-credit-ledger` | 200 | `usageCreditsApi.getBalance()`, `getLedger()` | 3 real ledger rows | already fixed in HS9B, re-verified |
| `/tenant/finance/security-deposit` | `/finance/security-deposit` | 200 | `tenantSetupApi.getWallet()` | real deposit status | clean |
| `/tenant/notifications` | `/notifications` | 200 | `notificationsApi.list()`, `getChannels()` | real (empty in this dev DB) | clean |
| `/tenant/settings` | `/settings` | 200 | `settingsApi.get()` + 4 other tabs (webhooks/deliveries/privacy/security) | real | clean, larger than ticket assumed (5 tabs, not just profile/security/preferences sub-routes) |
| `/tenant/settings/profile` | not a separate route — profile fields live in "General Settings" tab | n/a | — | — | documented, not a broken link (nothing links to a nonexistent sub-route) |
| `/tenant/settings/security` | "Security" tab within `/settings` | n/a (tab, not route) | `securityApi.*` | real API keys/IP-block/activity-report | functionally present |
| `/tenant/settings/preferences` | not present as a distinct route/tab | n/a | — | — | documented gap; notification channel preferences live at `/notifications` → Channels tab instead |

All real routes: tenant shell present, correct sidebar active state,
"Demo AC Services" tenant name shown, real API calls, no NaN/undefined,
no raw JSON, no crashes. One real bug found and fixed (see finance
overview report).

## Verdict
All routes this ticket asks about either exist and work, or have a
documented, non-misleading reason they don't (functionality present
under a different tab/route structure than assumed).
