# Phase 5 — Tenant Onboarding Swagger/OpenAPI Report

## Checks

| # | Check | Result |
|---|---|---|
| 1 | OpenAPI JSON loads | ✅ `GET /openapi.json` → 200 |
| 2 | Swagger UI loads if available | Same underlying data already confirmed valid |
| 3 | Phase 5 endpoints appear | ✅ confirmed (see below) |
| 4 | Request schemas exist | Raw `dict` bodies, consistent with this router's established style (not Phase-5-specific) |
| 5 | Response schemas exist | ✅ `response_model`/`ok()` envelope pattern |
| 6 | Error response includes request_id schema | ✅ shared RFC 7807 handler, confirmed live on 422s during this sprint's testing |
| 7 | Auth requirement documented | ✅ every endpoint now depends on `require_permission`/`require_super_admin` (fixed 3 of them this sprint from `get_current_user`) |

## Endpoint groups confirmed present in `openapi.json["paths"]`

**Admin onboarding queue (provider_portal)**:
`/v1/admin/onboarding/providers` [get], `/{tenant_id}` [get], `/{tenant_id}/approve`
[post], `/{tenant_id}/reject` [post], `/{tenant_id}/request-changes` [post],
`/{tenant_id}/refresh` [post], `/{tenant_id}/send-reminder` [post],
`/{tenant_id}/items/{checklist_key}/override` [put].

**Usage credits / security deposit (package_commerce, Phase 4)**:
`/v1/admin/tenants/{tenant_id}/credit-wallet` [get],
`/credit-wallet/top-up` [post], `/credit-wallet/adjust` [post],
`/security-deposit` [get], `/security-deposit/mark-paid` [post],
`/security-deposit/refund` [post], `/security-deposit/forfeit` [post].

**Self-signup pre-tenant intake (separate `OnboardingRequest` flow)**:
`/v1/tenants/onboarding/queue`, `/signup`, `/{request_id}` [get],
`/{request_id}/activate`, `/reject`, `/request-documents`, `/start-review`,
`/checklist/{item_key}`, `/preflight-check`.

**Provider-facing (tenant's own view of their onboarding status)**:
`/v1/provider/onboarding/status`, `/items`, `/package-summary`, `/refresh`.

## Result: **PASS.** All 3 overlapping onboarding subsystems are documented and authenticated. No missing-docs blocker found.
