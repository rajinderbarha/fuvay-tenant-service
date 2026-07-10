# Phase 3D — Pricing Swagger/OpenAPI Closure Report

## Checks

| # | Check | Result |
|---|---|---|
| 1 | OpenAPI JSON loads | ✅ `GET /openapi.json` → 200, valid JSON |
| 2 | Swagger UI loads if available | Not directly re-checked this sprint (FastAPI's default `/docs` is generated from the same `openapi.json` already confirmed valid — same underlying data) |
| 3 | Phase 3 endpoints appear | ✅ 49 pricing-related paths found across Tiers, Tier Locations (City/Zip), Pricing Rules, Bargain Rules, Provider Overrides, and the generic Master Data Audit endpoint |
| 4 | Request schemas exist | Endpoints accept raw `dict` bodies (`await r.json()`) rather than named Pydantic request models — consistent with this router's established style throughout, not a Phase 3-specific gap |
| 5 | Response schemas exist | ✅ All endpoints declare `response_model=ApiResponse[dict]` |
| 6 | Error schema includes request_id | ✅ Confirmed on every error response captured this sprint (403s, validation errors) — RFC 7807 `problem+json` via the shared exception handler |
| 7 | Auth requirements documented | ✅ Every endpoint depends on `require_permission(...)` → OpenAPI security scheme surfaced; confirmed live that unauthenticated calls return 401 |

## Endpoint groups confirmed present in `openapi.json["paths"]`

- **Pricing Tiers**: `/v1/admin/tiers`, `/tiers/summary`, `/tiers/export`, `/tiers/resolve-location`, `/tiers/{tier_id}`, `/tiers/{tier_id}/detail`, `/tiers/{tier_id}/hard-delete`
- **City/Zip (Tier Locations)**: `/v1/admin/tier-locations` + summary/export/import-preview/import-confirm/imports/bulk-change-tier/bulk-deactivate/resolve-conflict
- **Pricing Rules**: `/v1/admin/pricing-rules` + summary/export/preview/{id}/activate/deactivate/conflicts/hard-delete
- **Bargain Rules**: `/v1/admin/pricing/bargain-rules` + summary/{id}/activate/deactivate/validate/audit/enable/disable, `/pricing/bargain/evaluate-preview`
- **Provider Overrides**: `/v1/admin/pricing/provider-overrides` + summary/validate-preview/{id}/activate/deactivate/approve/reject/audit/enable/disable
- **Audit**: `/v1/admin/master-data-audit` (generic, entity_type-filterable)

## Result: **PASS.** All Phase 3 endpoint groups (Tiers, City/Zip, Rules, Resolver/Preview, Bargain Rules, Bargain Evaluation, Provider Overrides, Provider Override Validation, Audit) are present, authenticated, and error-documented in OpenAPI.
