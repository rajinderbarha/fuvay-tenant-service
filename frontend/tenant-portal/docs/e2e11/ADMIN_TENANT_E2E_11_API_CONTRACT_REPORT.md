# E2E-11 API Contract Report

## Finance Pages

| Page | API Function | Endpoint Category | Real? |
|------|-------------|-------------------|-------|
| `/finance/package` | `tenantSetupApi.getPackage()` | tenant package | YES |
| `/finance/package` | `usageCreditsApi.getBalance()` | usage credits (HS9/HS9B) | YES |
| `/finance/usage-credit-ledger` | `usageCreditsApi.getBalance()` | usage credits | YES |
| `/finance/usage-credit-ledger` | `usageCreditsApi.getLedger()` | usage credits | YES |
| `/finance/security-deposit` | `tenantSetupApi.getWallet()` | tenant wallet (deposit sub-key) | YES |

## Notifications Page

| Function | Purpose | Real? |
|----------|---------|-------|
| `notificationsApi.list()` | Notification history | YES |
| `notificationsApi.getChannels()` | Channel config | YES |
| `notificationsApi.setChannel()` | Toggle channel | YES |

## Settings Page

| Function | Purpose | Real? |
|----------|---------|-------|
| `settingsApi.*` | General settings CRUD | YES |
| `complianceApi.*` | Consent / DPDP / export / deletion | YES |
| `securityApi.*` | API keys / IP / alerts | YES |

## Previously Removed Stale APIs
- `tenantSetupApi.getWallet()` was removed from balance display (E2E-11 fix) — it returned Sprint 23 wallet/invoice concept, not usage credits
- Replaced with `usageCreditsApi.getBalance()` for the balance card

## Status: PASS
