# Phase 3 — Pricing & Rules Frontend/Backend Integration Report

| # | Check | Result |
|---|---|---|
| 1 | Pricing Tiers page uses correct backend endpoint | ✅ `catalogApi.listTiers` → `GET /v1/admin/tiers` |
| 2 | City/Zip Mapping page uses correct backend endpoint | ✅ `catalogApi.listTierLocationsGrid` → `GET /v1/admin/tier-locations` |
| 3 | Pricing Rules page uses correct backend endpoint | ✅ `catalogApi.listPricingRules` → `GET /v1/admin/pricing-rules` |
| 4 | Price Preview calls real resolver endpoint | ✅ `catalogApi.previewPricingRule` → `POST /v1/admin/pricing-rules/preview`; live-verified `final_customer_estimate: 800.0` |
| 5 | Bargain Rules page uses correct backend endpoint | ✅ `bargainRulesApi.list` → `GET /v1/admin/pricing/bargain-rules`, live-verified |
| 6 | Bargain Preview calls real evaluation endpoint | ✅ `bargainRulesApi.evaluatePreview` → `POST /v1/admin/pricing/bargain/evaluate-preview`, live-verified all 5 offer scenarios |
| 7 | Provider Overrides page uses correct backend endpoint | ✅ `providerOverridesApi.list/create/approve/reject` → `/v1/admin/pricing/provider-overrides*`, live-verified all 3 price scenarios |
| 8 | Create/edit payloads match backend schemas | ✅ `BargainRule`/`ProviderPricingOverride` TS interfaces mirror the Pydantic-free dict responses from `_bargain_rule_dict`/`_override_dict` field-for-field |
| 9 | Frontend displays backend validation errors | ✅ `createAction.error`/`rejectAction.error` rendered inline in both new modals (same pattern as Checklists/Issue Types) |
| 10 | Frontend displays backend request_id on error | ✅ `EmptyState` on both new pages renders `list.requestId` from `useApi` |
| 11 | Frontend does not use mock data when backend has records | ✅ both new pages call real API clients exclusively, no `MOCK_*` imports |
| 12 | Frontend does not show blank pages if backend has data | ✅ confirmed live — both pages return 200 and render real data from the seeded bargain rule / provider override |
| 13 | Frontend labels match ServiceOS business rules | ✅ "Bargain Floor", "Override Price", "Completed Job Deduction" used throughout; no forbidden cash/wallet/payout language |

**All 13 integration checks pass.**

## Field-name spot-check

Compared live API responses against the new TypeScript interfaces:
- `BargainRule.floor_amount` ↔ backend `floor_amount` (float) — match.
- `ProviderPricingOverride.approval_status` ↔ backend `approval_status` —
  match, values `pending`/`approved`/`rejected` used identically on both
  sides.
- `PricingPreviewResult.completed_job_deduction_credits` ↔ backend
  `completed_job_deduction_credits` (int) — match, confirmed `21` live.
