# Phase 3 — Pricing & Rules Frontend Report

| Module | Page | Status |
|---|---|---|
| Pricing Tiers | `/admin/pricing-tiers` | ✅ pre-existing, unchanged, confirmed working |
| City/Zip Mapping | `/admin/location-mapping` | ✅ pre-existing, unchanged, confirmed working |
| Pricing Rules | `/admin/pricing-rules` | ✅ pre-existing, unchanged — now also displays `completed_job_deduction_credits` via the updated `PricingRule`/`PricingPreviewResult` TS interfaces |
| Bargain Rules | `/admin/pricing/bargain-rules` | ✅ **built this sprint** |
| Provider Pricing Overrides | `/admin/pricing/provider-overrides` | ✅ **built this sprint** |

## New pages built this sprint

**`/admin/pricing/bargain-rules`** — summary-free list (table: Rule / Bargain
Floor / Below-Floor Action / Provider Approval / Bargaining Enabled /
Status / Actions), "New Bargain Rule" create modal (category → master
service cascading selector, floor amount, enabled/approval-required
toggles), and an "Evaluate Offer" modal that calls the real
`bargainRulesApi.evaluatePreview` endpoint and renders accepted/rejected
with the reason and floor value — no mock data.

**`/admin/pricing/provider-overrides`** — table (Tenant / Override Price /
Reason / Approval / Status / Actions), "New Override" create modal (tenant
selector via `adminTenantsApi.list`, category → service cascading selector,
override price, reason), inline Approve/Reject actions for pending
overrides with a required-reason reject modal.

Both follow the same enterprise dark-theme pattern established across
Phase 2 (`AdminLayout` + `Card`/`DataTable`/`Modal`/`Badge` from
`components/shared/ui.tsx`, `SectionHeader`, toast notifications, error
states showing `requestId` from `useApi`).

## Sidebar

`AdminLayout.tsx`'s "Pricing" group renamed to **"Pricing & Rules"**
(matching the ticket's exact required label) and extended with the 2 new
items — 5 total: Pricing Tiers, City/Zip Mapping, Pricing Rules, Bargain
Rules, Provider Pricing Overrides. Each label confirmed to appear exactly
once (`grep -c` check in the regression test suite).

## Forbidden labels

Grepped all pricing backend + frontend source (service.py, admin_router.py,
pricing_engine.py, both new pages) for `cash_wallet`, `tenant_payout`,
`earnings_wallet`, `escrow` — **zero occurrences**. All labels use the
ServiceOS-correct terminology: "Base Price", "Bargain Floor", "Provider
Pricing Override", "Completed Job Deduction" (credits, never cash).

## TypeScript

`npx tsc --noEmit` → **0 errors** across the entire `frontend/super-admin`
build, including both new pages and the `lib/api.ts` additions
(`bargainRulesApi`, `providerOverridesApi`, updated `PricingRule`/
`PricingPreviewResult` interfaces).

**All frontend hard gates PASS.**
