# Phase 1 — Admin Setup Frontend/Backend Integration Report

| # | Check | Result |
|---|---|---|
| 1 | Frontend auth uses correct login endpoint | ✅ `authApi.login` → `POST /v1/auth/login` |
| 2 | Frontend current user uses correct /auth/me endpoint | ✅ confirmed in `AdminLayout`/login flow |
| 3 | Sidebar uses backend effective-menu endpoint | ✅ `verticalCatalogApi.getEffectiveMenu()` → `GET /v1/admin/catalog/navigation/effective-menu`, live 200 |
| 4 | Platform Settings UI field names match backend setting keys | ✅ all 11 Home Services keys confirmed identical frontend/backend (Phase 0 report) |
| 5 | Engine UI field names match backend engine schema | ✅ `/admin/engines` consumes `engine_key`/`lifecycle_status`/`health_status` fields matching `GET /v1/admin/engines` response shape |
| 6 | Vertical UI field names match backend vertical schema | ✅ `/admin/verticals` consumes `key`/`is_enabled`/`is_beta` matching live response |
| 7 | Roles UI field names match backend role/permission schema | ⚠️ N/A — no dedicated Roles UI exists (see frontend report); Users page's role dropdown uses the same role string values as the backend `role` column |
| 8 | Audit UI field names match backend audit schema | ✅ 3-tab Audit Logs page (`engine`/`security`/`auth`) each map 1:1 to their respective backend endpoint's field names |
| 9 | Frontend handles backend validation errors | ✅ Platform Settings save flow surfaces `VALIDATION_ERROR` responses (confirmed in the earlier Phase 1 sprint's bug-fix work) |
| 10 | Frontend handles 401/403/404/422/500 | ✅ `lib/api.ts` has centralized error handling + 401 refresh-retry logic (confirmed Phase 0/1); 403/404/422 surface `error_code`+`detail`+`request_id` via the standard `apiFetch` error path |
| 11 | Frontend does not use mock runtime data if backend data exists | ✅ all 10 Phase 1 module pages call real API clients, no `MOCK_*` imports found |
| 12 | No hardcoded stale sidebar | ✅ `NAV_GROUPS` in `AdminLayout.tsx` is a static base structure (labels/icons/routes), but visibility/enablement is dynamically resolved from `effectiveMenu` at runtime — not "hardcoded data," hardcoded *structure* which matches this repo's established Sprint 34K nav-config pattern |

**11/12 checks fully pass; 1 is N/A due to a genuine missing feature (dedicated
Roles UI) rather than an integration defect** — the Users page's role field
does correctly integrate with the backend's real role values, it's just not
a full CRUD management surface.

## Data consistency spot-check

Compared this sprint's live API responses against what the corresponding
frontend page's TypeScript interfaces expect (`lib/api.ts`):
- `EngineListItem` interface fields (`engine_key`, `lifecycle_status`,
  `health_status`, `is_core`, `is_locked`) — all present in the live
  `GET /v1/admin/engines/health` response.
- `PlatformSetting` interface fields (`key`, `value`, `type`, `risk_level`,
  `requires_approval`) — all present in the live `GET /v1/admin/settings`
  response.
- No field-name mismatches found.
