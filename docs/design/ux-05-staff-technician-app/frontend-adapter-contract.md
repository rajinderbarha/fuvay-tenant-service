# Frontend Adapter Contract

Every adapter below documents: intended route, request/response shape, required role/permission, StaffPermission
behavior, mutation scope, error mapping, cache behavior, offline behavior, retry, readiness. Real adapters are
the actual functions in `src/lib/api.ts` (all calls in this app already go through this one file — a real,
pre-existing convention, not introduced by UX-05). Mock adapters describe the intended shape for endpoints that
don't exist yet.

## Auth / Session — REAL
| | |
|---|---|
| Route | `POST /v1/auth/login`, `GET /v1/auth/me`, `POST /v1/auth/logout` |
| Request/Response | `{email,password} -> {access_token,refresh_token,user:{id,email,full_name,role,tenant_id,phone,is_active,...},tenant:{...}}`; `me() -> StaffUser` |
| Role/Permission | None (public login); `me`/`logout` require a bearer token |
| StaffPermission | N/A |
| Mutation scope | Session only (token storage in AsyncStorage) |
| Error mapping | `ServiceOSError{code,message,resolution,status}` — Round 7 added real `status` so a 401 on `me()` can be distinguished as session-expired (see `AuthContext.tsx`) |
| Cache behavior | Token persisted in AsyncStorage; `StaffUser` held in React state only, refetched on app start |
| Offline behavior | Login is `online_required`; a cached token allows optimistic `loading` state until `me()` resolves/fails |
| Retry | None automatic |
| Readiness | `production_ready` |

**UX-05B FIX 1 correction (this doc previously described a route that never existed).** This section originally
documented `POST /v1/auth/staff/login` with `{phone,password} -> {access_token,refresh_token,staff:StaffUser}`.
That route does not exist — confirmed live (`405`, not present in the OpenAPI spec) — and the app's login screen
was, in reality, completely broken from before UX-05 began (traced via `git blame` to baseline commit `36efe8d`,
predating all UX-05 work; the same class of "calls a nonexistent endpoint" defect MODULE-L5-33/34/35/36 already
fixed elsewhere in this app, but login itself was never swept). The real, confirmed-live contract — the same
`POST /v1/auth/login` endpoint the super-admin and tenant-portal web apps already use — takes `{email,password}`
and returns `{access_token,refresh_token,user:{...},tenant:{...}}`, unwrapped from a `{data:...}` envelope by the
existing `apiFetch` helper. `authApi.login`, `AuthContext.login()`, and `LoginScreen.tsx`'s form field were all
updated to match (email instead of phone). See `prerequisite-bug-fix-report.md` for the fix account and evidence.

## Home (Technician) — REAL (partial: technician home real, staff home mock)
| | |
|---|---|
| Route | `GET /v1/staff/service-jobs` (jobs), `GET /v1/staff/notifications/unread-count` |
| Request/Response | `JobListResponse{jobs,count}`; `{unread_count}` |
| Role/Permission | Any authenticated staff-app user |
| StaffPermission | N/A (technician home shows only the caller's own jobs) |
| Mutation scope | Read-only |
| Error mapping | Standard `ServiceOSError` |
| Cache behavior | `useApi` hook — no cross-screen cache, refetched per mount |
| Offline behavior | `view_cached` (last successful response usable while stale) |
| Retry | Manual pull-to-refresh only |
| Readiness | `production_ready` (technician); `api_contract_required` (staff — no work-queue-summary endpoint) |

## My Work — REAL
| | |
|---|---|
| Route | Same `GET /v1/staff/service-jobs`, filtered client-side via `groupJobs()`/`classifyJob()` (`src/lib/ux05/myWork.ts`) |
| Request/Response | Same `JobListResponse` |
| Role/Permission | Any authenticated staff-app user |
| StaffPermission | N/A |
| Mutation scope | Read-only |
| Error mapping | Standard |
| Cache behavior | Same as Home |
| Offline behavior | `view_cached` |
| Retry | Manual pull-to-refresh |
| Readiness | `production_ready` |

## Schedule — REAL
| | |
|---|---|
| Route | Same `GET /v1/staff/service-jobs`, grouped client-side by `scheduled_date` (no per-day schedule endpoint exists) |
| Request/Response | Same `JobListResponse` |
| Role/Permission | Any authenticated staff-app user |
| StaffPermission | N/A |
| Mutation scope | Read-only |
| Error mapping | Standard |
| Cache behavior | Same as Home |
| Offline behavior | `view_cached` |
| Retry | Manual pull-to-refresh |
| Readiness | `production_ready` (Today/Upcoming only — no Day/Agenda toggle, no conflict detection) |

## Job Detail (ServiceJob) — REAL
| | |
|---|---|
| Route | `GET /v1/staff/service-jobs/{id}` -> `{job,assignment,booking}` |
| Request/Response | `JobDetail` (unwrapped from a `{success,data}` or bare-object envelope depending on the underlying engine — see `_unwrapAssignmentResult` in `lib/api.ts`) |
| Role/Permission | Job must be assigned to the caller |
| StaffPermission | N/A (technician sees only their own assignment) |
| Mutation scope | Read-only for this adapter; see Status Transition below for mutations |
| Error mapping | Standard; a 404-equivalent renders "Job not found or not assigned to you" |
| Cache behavior | Per-screen, refetched on mount and after every transition |
| Offline behavior | `view_cached` |
| Retry | Manual (`detail.refetch()` after any successful action) |
| Readiness | `production_ready` |

## Status Transition — REAL
| | |
|---|---|
| Route | `POST /v1/staff/service-jobs/{id}/{accept\|reject\|on-the-way\|reached-site\|start-inspection\|complete-inspection\|start-service\|work-done\|complete}` — 9 distinct real endpoints, no generic status-PUT |
| Request/Response | `reject` needs `{reason}`; `complete` needs `{work_summary,collected_amount,payment_mode}`; others take no body |
| Role/Permission | Job must be assigned to the caller |
| StaffPermission | N/A |
| Mutation scope | One job's status per call |
| Error mapping | Standard; validation errors (e.g. `WORK_SUMMARY_REQUIRED`) surfaced as `actionState.error` |
| Cache behavior | N/A (mutation) |
| Offline behavior | `online_required` — always, no exceptions (no idempotency key on any of these 9 endpoints) |
| Retry | None automatic — never auto-replayed |
| Readiness | `production_ready` |

## Notifications — REAL
| | |
|---|---|
| Route | `GET /v1/staff/notifications`, `GET .../unread-count`, `POST .../{id}/read`, `POST .../mark-all-read` |
| Request/Response | `NotificationListResponse{items,total,unread_count}`; `StaffNotification` |
| Role/Permission | Any authenticated staff-app user |
| StaffPermission | N/A |
| Mutation scope | Read-state per notification or all |
| Error mapping | Standard |
| Cache behavior | Refetched per screen mount |
| Offline behavior | `view_cached` for list; mark-read is `online_required` |
| Retry | None automatic |
| Readiness | `production_ready` |

## Chat — REAL (not UX-05-built, pre-existing)
| | |
|---|---|
| Route | `GET /v1/staff/chat/threads`, `GET .../{id}/messages`, `POST .../{id}/messages`, `POST .../{id}/read` |
| Readiness | `production_ready` (pre-existing, unrelated to UX-05) |

## Profile / Performance — REAL (partial)
| | |
|---|---|
| Route | `GET /v1/staff/{id}`, `GET /v1/ds/tenants/{tid}/staff/{sid}/score`, `PUT /v1/staff/{id}/schedule` |
| Request/Response | `StaffUser`; `StaffPerformance`; `{working_hours} -> StaffUser` |
| Role/Permission | Own profile only |
| StaffPermission | N/A |
| Mutation scope | Own working-hours schedule |
| Error mapping | A 404 on the score endpoint is a legitimate "no score computed yet" state, not an error |
| Cache behavior | Per-screen |
| Offline behavior | `view_cached` for read; schedule update is `online_required` |
| Retry | None automatic |
| Readiness | `production_ready` (specialisations/schedule/performance real); `mock_design_only` (areas/certifications/supported-brands/recent-activity — no such fields exist) |

---

## MOCK_DESIGN_ONLY adapters (no live endpoint — intended shape only)

| Adapter | Intended route (not real) | Request/Response shape | Permission | Readiness |
|---|---|---|---|---|
| Inspection | `POST/GET /v1/staff/service-jobs/{id}/inspection` (not real) | `InspectionDraftView` | Job assigned to caller | `api_contract_required` |
| Checklist | `POST/GET /v1/staff/service-jobs/{id}/checklist` (not real) | `ChecklistExecutionView` | Job assigned to caller | `api_contract_required` |
| Quote | `GET/POST /v1/staff/service-jobs/{id}/quote` (not real) | `QuoteSummaryView` | Job assigned to caller (technician: draft/edit only, never approve) | `api_contract_required` |
| Parts Request (create/track) | `POST/GET /v1/staff/service-jobs/{id}/parts-requests` (not real) | `PartsRequestDraftView` / `PartsRequestStatusView` | Job assigned to caller; ServiceJob-only | `api_contract_required` |
| Staff Parts Approval | `POST /v1/staff/parts-requests/{id}/{approve\|reject}` (not real) | `PartsApprovalQueueItemView` | `parts_request:approve` StaffPermission (no fetch endpoint for this exists either) | `api_contract_required` + `product_decision_required` |
| Job Notes | `POST/GET /v1/staff/service-jobs/{id}/notes` (not real) | `JobNoteView[]` | Job assigned to caller; visibility enforced client-side pending real backend enforcement | `api_contract_required` |
| Job Media | `POST /v1/staff/service-jobs/{id}/media` (not real) | `JobMediaView` (never storage keys/signed URLs) | Job assigned to caller | `api_contract_required` |
| Availability/Work-Status | `PUT /v1/staff/{id}/availability` (not real) | `AvailabilityView.workStatus` | Own account only | `api_contract_required` |
| Staff Work Queue | `GET /v1/staff/work-queue` (not real) | `WorkQueueItemView[]` | Requires real role/permission field on `StaffUser` (doesn't exist) | `api_contract_required` + `product_decision_required` |
| StaffPermission fetch | `GET /v1/staff/{id}/permissions` (not real) | `StaffPermissionView[]` | N/A (this IS the permission-fetch endpoint) | `api_contract_required` + `product_decision_required` |

All MOCK_DESIGN_ONLY adapters' consuming screens are dev-only showcases, never linked from production
navigation, and every screen carries an explicit on-screen `MOCK_DESIGN_ONLY` disclosure string.
