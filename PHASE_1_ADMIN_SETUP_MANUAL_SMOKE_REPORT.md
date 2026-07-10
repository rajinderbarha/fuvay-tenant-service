# Phase 1 — Admin Setup Manual Browser Smoke Report

## Explicit limitation

**No real browser was launched this sprint**, same as Phase 0. All 27 smoke
steps below are broken down into what was verified via API/DB checks versus
what remains unverified pending an actual browser walkthrough.

| # | Step | Verified how | Status |
|---|---|---|---|
| 1-2 | Start backend/frontend | Backend started (`uvicorn`), frontend dev server not started | ⚠️ backend only |
| 3 | Login as Super Admin | `POST /v1/auth/login` → 200 | ✅ API-level |
| 4 | Dashboard loads | `GET /v1/admin/dashboard/executive-summary` → 200, zero-state fields valid | ✅ API-level |
| 5 | Current admin user appears | `GET /v1/auth/me` → 200 | ✅ API-level |
| 6-7 | Sidebar / no duplicate Brands/Pricing | Static-verified `AdminLayout.tsx` | ✅ source-level |
| 8-9 | Roles page / required roles | **No dedicated Roles page exists** | ❌ not applicable — feature gap |
| 10-11 | Permissions page / required permissions | **No dedicated Permissions page exists** | ❌ not applicable — feature gap |
| 12-13 | Platform Users page / users exist | `GET /v1/admin/platform-users` → 200, real data | ✅ API-level |
| 14-15 | Platform Settings / Home Services values | Confirmed exactly correct (Phase 0 report) | ✅ API-level |
| 16 | Update one safe setting with reason, revert | Performed and confirmed in the earlier Phase 1 sprint (`allow_reschedule` toggle + audit log) | ✅ API-level (from prior sprint) |
| 17-18 | Engine Management / required engines | `GET /v1/admin/engines/summary` confirmed 39 engines, 0 disabled | ✅ API-level |
| 19-20 | Vertical Configuration / Home Services enabled | `GET /v1/admin/verticals` confirmed | ✅ API-level |
| 21-22 | Restricted admin / forbidden actions blocked | `provider@serviceos.in` (tenant_owner) → 403 on settings update, confirmed live | ✅ API-level |
| 23-24 | Audit Logs / actions recorded | `GET /v1/admin/audit-logs` confirmed `setting.changed` entries from step 16; login events confirmed via `/v1/auth/audit-log` | ✅ API-level |
| 25 | Trigger forbidden action, confirm 403 + request_id | Same as step 21-22, `request_id` present in response | ✅ API-level |
| 26 | No browser console errors | Not checked — no browser was opened | ❌ not run |
| 27 | No NaN/null/undefined in UI | Not visually checked; backend zero-state values confirmed as proper `0` integers (not `null`), reducing but not eliminating risk of a frontend rendering bug | ⚠️ partial |

## Why the browser step was skipped

Same reasoning as Phase 0: this session has no interactive browser tooling
invoked, and the volume of already-completed API/DB-level verification
covers the substance of nearly every smoke step. Two steps are genuinely
inapplicable (no Roles/Permissions pages exist to smoke-test).

**Per the ticket's own rule: "If manual browser smoke is skipped →
PARTIAL_READY_WITH_ADMIN_SETUP_BLOCKERS."**
