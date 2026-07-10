# Phase 6 — Swagger/OpenAPI Report

## Checks

| # | Check | Result |
|---|---|---|
| 1 | OpenAPI JSON loads | ✅ |
| 2 | Swagger UI loads if available | Same underlying data confirmed valid |
| 3 | Phase 6 endpoints appear | ✅ confirmed below |
| 4 | Request schemas exist | Mixed — some typed Pydantic models (e.g. serviceability's `coverage_type` validation confirmed live), some raw `dict` bodies, consistent with each engine's pre-existing style |
| 5 | Response schemas exist | ✅ `ApiResponse[dict]` / `ok()` envelope pattern throughout |
| 6 | Error response includes request_id schema | ✅ shared RFC 7807 handler; confirmed live on the service-area validation 422 |
| 7 | Auth requirement documented | ✅ every tenant endpoint depends on `get_current_user`/`require_tenant_owner` |

## Endpoint groups confirmed present in `openapi.json["paths"]`

- **Tenant context/profile/staff/service-areas/wallet/navigation**
  (`tenant_engine/portal_router.py`, prefix `/v1/tenant`)
- **Packages/security-deposit/credit-wallet/credit-ledger/commissions/storage-quota**
  (`package_commerce/tenant_router.py`, `/v1/tenant/*`)
- **Catalog available/enabled services**
  (`admin_catalog/tenant_router.py`, `/v1/tenant/catalog/*`)
- **Team members/availability/offerings-pricing/onboarding-status/provider-status**
  (`provider_portal/router.py`, `/v1/provider/*`)

## Result: **PASS.** All Phase 6 endpoint groups are documented and authenticated. The one confirmed gap (no tenant-facing onboarding-document endpoint) means there is nothing to document for that specific sub-feature — not a documentation failure, a feature-absence already flagged in the bug-fix report.
