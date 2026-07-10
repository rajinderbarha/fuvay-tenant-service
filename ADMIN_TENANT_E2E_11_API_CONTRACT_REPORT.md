# ADMIN-TENANT-E2E-11 — API Contract Report

## Actual API client functions (this codebase's real `lib/api.ts`, not
the ticket's assumed `src/lib/api/tenant-*.ts` module split)

| Ticket's assumed function | Real equivalent |
|---|---|
| `getTenantFinanceOverview()` | `tenantSetupApi.getPackage()` + `getWallet()` |
| `getTenantUsageCreditBalance()` | `usageCreditsApi.getBalance()` → `GET /v1/provider/usage-credits/balance` |
| `getTenantUsageCreditLedger()` | `usageCreditsApi.getLedger()` → `GET /v1/provider/usage-credits/ledger` |
| `getTenantSecurityDeposit()` | `tenantSetupApi.getWallet()` (deposit is a field within the wallet response) |
| `getTenantCreditAlerts()` | folded into `usageCreditsApi.getBalance()`'s `low_credit` boolean |
| `getTenantNotifications()` | `notificationsApi.list()` → `GET /v1/notifications/tenants/{tid}/list` |
| `getTenantUnreadNotificationCount()` | **does not exist** — this notification model has no read/unread concept (delivery-log statuses only) |
| `markTenantNotificationRead()` | **does not exist**, same reason |
| `getTenantSettings()` | `settingsApi.get()` → `GET /v1/settings/tenants/{tid}` |
| `updateTenantSettings()` | `settingsApi.update()` → `PUT /v1/settings/tenants/{tid}/{key}` |
| `getTenantNotificationPreferences()` | `notificationsApi.getChannels()` → `GET /v1/notifications/tenants/{tid}/channels` |
| `updateTenantNotificationPreferences()` | `notificationsApi.setChannel()` → `PUT .../channels/{channel}` |

## Rules checked
1. Central API client used — yes, throughout (see direct-fetch scan).
2. Auth token included — confirmed, `apiFetch` attaches
   `serviceos_tenant_token` automatically.
3. Tenant context included — confirmed, every call above is either
   tenant-scoped by path (`/tenants/{tid}/...`) or infers the tenant from
   the authenticated session (`/v1/provider/usage-credits/*`).
4. `request_id` parsed — confirmed, present in every response's `meta`,
   surfaced via `useApi().requestId` in error states.
5. No direct fetch in page components — confirmed (see direct-fetch
   scan).
6. No fake runtime data — confirmed (see mock-data scan).
7. Mutations refetch/invalidate — confirmed: `updateSetting`,
   `toggleConsent`, webhook create/delete/pause/resume, security-key
   create/rotate/revoke all call `.refetch()` on their related `useApi`
   hook after a successful mutation.

## Verdict
Real APIs used throughout, correctly wired, request_id surfaced on
errors, mutations refetch. The one gap (`updateTenantSettings` being
callable by a role that shouldn't be able to) is a permission-layer
issue, not an API-contract issue — the contract itself (auth header,
tenant scoping, request_id, refetch-after-mutate) is followed correctly.
