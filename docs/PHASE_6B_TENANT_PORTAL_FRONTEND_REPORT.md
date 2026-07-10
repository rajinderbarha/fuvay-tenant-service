# Phase 6B — Tenant Portal Enterprise UI Frontend Report

## Pages Upgraded

| Page | Path | Action |
|------|------|--------|
| Dashboard | /dashboard | Rewritten — enterprise 8-card summary, setup checklist, finance snapshot, quick links |
| Provider Wallet | /provider/wallet | Forbidden label fix — "Available Balance" → "Usage Credit Balance" |
| Finance | /finance | Forbidden label fix — "Wallet Balance" → "Usage Credit Balance" |
| Analytics | /analytics | Forbidden label fix |
| Analytics Financial | /analytics/financial | Forbidden label fix |
| Field Labels | lib/field-labels.ts | wallet_balance label fixed |

## New Pages Created

| Page | Path |
|------|------|
| Package & Credits | /finance/package |
| Usage Credit Ledger | /finance/usage-credit-ledger |
| Security Deposit | /finance/security-deposit |
| Pricing Setup | /provider/pricing |
| Activity & Audit Log | /activity |

## Navigation Updated
- nav-config.ts rewritten with enterprise groups: Overview, Setup, Team, Finance, More, Operations, Engagement, Insights
- Path-to-nav-id mappings updated for all new routes
