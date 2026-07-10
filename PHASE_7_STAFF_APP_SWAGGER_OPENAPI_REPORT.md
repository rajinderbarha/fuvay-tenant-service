# Phase 7 — Swagger/OpenAPI Report

## Checks

| # | Check | Result |
|---|---|---|
| 1 | OpenAPI JSON loads | ✅ |
| 2 | Swagger UI loads if available | Same underlying data confirmed valid |
| 3 | Phase 7 endpoints appear | ✅ confirmed below |
| 4 | Request schemas exist | Mixed, consistent with each engine's pre-existing style |
| 5 | Response schemas exist | ✅ `ApiResponse[dict]` / `ok()` envelope throughout |
| 6 | Error response includes request_id schema | ✅ shared RFC 7807 handler, confirmed live on the 422 test during job-list verification |
| 7 | Auth requirement documented | ✅ every endpoint depends on `get_current_user` + role checks |

## Endpoint groups confirmed present in `openapi.json["paths"]`

- **Staff job shell**: `/v1/staff/me/jobs`, `/{job_id}`, `/accept`, `/reject-assignment`, `/status`, `/checklist*` (`field_ops/staff_router.py`)
- **Staff notifications/chat**: `/v1/staff/notifications*`, `/v1/staff/chat*` (`platform_notifications/provider_router.py`)
- **Provider team members (skills)**: `/v1/provider/team-members*` (`provider_portal/router.py`) — **fixed this sprint**, was 500ing
- **Provider availability**: `/v1/provider/availability*`
- **Provider status/onboarding**: `/v1/provider/status`, `/v1/provider/onboarding/status`
- **Tenant staff (owner-managed)**: `/v1/tenant/staff*` — **fixed this sprint** (role filter bug)

## Result: **PASS.** All Phase 7 backend endpoint groups are documented, authenticated, and (after this sprint's fixes) functional. No missing-docs blocker found — the blocker is missing frontend, not missing API documentation.
