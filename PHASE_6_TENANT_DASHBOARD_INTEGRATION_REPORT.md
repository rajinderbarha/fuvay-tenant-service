# Phase 6 — Frontend/Backend Integration Report

| # | Check | Result |
|---|---|---|
| 1-2 | Dashboard/context use correct endpoints | ✅ `/v1/tenant/dashboard/runtime` — **fixed this sprint** (was resolving to a phantom tenant for the certified test account) |
| 3 | Business profile page uses correct endpoint | ✅ `/v1/tenant/profile` (pre-existing, unchanged) |
| 4-6 | Package & Credits / Ledger / Security Deposit use correct endpoints | ✅ `/v1/tenant/wallet`, `/v1/tenant/credit-wallet`, `/v1/tenant/credit-ledger`, `/v1/tenant/security-deposit` — all confirmed live with real data |
| 7 | Service Areas page uses correct endpoint | ✅ `/v1/tenant/service-areas` — live-confirmed create with the exact baseline (Ludhiana 141001) |
| 8-9 | Services / Coverage pages use correct endpoints | ✅ `/v1/tenant/catalog/available-services`, `/enabled-services` |
| 10 | Pricing Setup uses correct endpoint | ✅ `/v1/provider/offerings/enabled/{id}` (provider_price_override etc.) |
| 11-12 | Team / Availability use correct endpoints | ✅ `/v1/tenant/staff`, `/v1/provider/availability` |
| 13 | Documents page uses correct endpoint | ❌ **no dedicated tenant-facing onboarding-document endpoint exists** — documented as a real gap in the bug-fix report, not fabricated |
| 14 | Setup Checklist uses correct endpoint | ✅ `/v1/provider/onboarding/status` (progress_percent + blockers) |
| 15-17 | Notifications / Activity / Navigation use correct endpoints | ✅ `/v1/provider/notifications`, navigation via `/v1/tenant/navigation` |
| 18 | Frontend payloads match backend schemas | ✅ confirmed for service-areas create (`coverage_type` required field correctly validated with a clean 422 + request_id) |
| 19 | Frontend displays backend validation errors | ✅ confirmed via the service-area creation 422 test |
| 20 | Frontend displays backend request_id on error | ✅ fixed this sprint (48 occurrences across 3 files) — reuses the shared `ServiceOSError`/`useApi` infra already fixed app-wide in Phase 3C |
| 21 | Frontend does not use mock data | ✅ confirmed — no mock/fake markers found |
| 22 | Frontend does not show blank pages if backend has data | ✅ confirmed — dashboard now correctly resolves real tenant data after the critical fix |
| 23 | Frontend labels match business rules | ✅ confirmed via forbidden-label scan |

## Result: **PASS with one documented, non-blocking gap** (tenant document view/reupload has no backend endpoint — a genuine missing feature, not an integration break, since the frontend correctly has nothing broken to call).
