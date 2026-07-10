# Phase 1B — Manual Browser Smoke Report

## Environment limitation (must be stated upfront)

This session has **no interactive browser automation tool available**
(no Playwright/Puppeteer/Chrome DevTools MCP; `WebFetch` was attempted
against `http://localhost:3000/admin/users/roles` and rejected with
"Invalid URL" — it does not support local/non-HTTPS URLs). This is a hard
environment constraint, not a choice to skip the step.

**What changed vs. Phase 0/1's smoke reports**: this sprint went
substantially further than before — it actually started both the real
backend (`uvicorn`) and the real frontend (`npm run dev`, Next.js dev
server) and hit every target page over HTTP, confirming server-side
rendering succeeds (200, no crash) for all of them, in addition to the
full API-level walkthrough. This is **still not** a true browser session:
no JavaScript execution, no client-side data-fetch confirmation, no visual
console-error check, no interactive click-through.

## Step-by-step

| # | Step | Verified how | Status |
|---|---|---|---|
| 1 | Start backend | `uvicorn app.main:app` → `/health` 200 | ✅ |
| 2 | Start admin frontend | `npm run dev` → port 3000, `/login` → 200 | ✅ **new this sprint** |
| 3 | Login as Super Admin | `POST /v1/auth/login` → 200 | ✅ API-level |
| 4 | Dashboard loads | `GET /v1/admin/dashboard/executive-summary` → 200; `curl http://localhost:3000/admin/dashboard` → 200 (SSR shell, no crash) | ✅ API + SSR-level |
| 5 | Current admin user appears | `GET /v1/auth/me` → 200 | ✅ API-level |
| 6 | Open sidebar | Static-verified `AdminLayout.tsx`, now includes new Roles/Permissions items | ✅ source-level |
| 7 | No duplicate Brands/Pricing | Static-verified, unchanged | ✅ source-level |
| 8-9 | Platform Users load | `GET /v1/admin/platform-users` → 200; page SSR → 200 | ✅ |
| 10-11 | Roles page loads from real API | `GET /v1/admin/roles` → 200, 10 roles returned; `curl http://localhost:3000/admin/users/roles` → 200 | ✅ **new this sprint** |
| 12-13 | Permissions page loads from real API | `GET /v1/admin/permissions` → 200, 335 permissions; page SSR → 200 | ✅ **new this sprint** |
| 14-15 | Platform Settings / 11 Home Services values | Confirmed exactly correct (Phase 0/1 reports, re-verified via same live endpoint) | ✅ |
| 16-19 | Update setting with reason, confirm audit, revert, confirm audit again | Performed and confirmed in the earlier Phase 1 sprint (`allow_reschedule` toggle) — not re-executed this sprint to avoid redundant audit-log noise, but the underlying endpoint is unchanged and re-confirmed reachable | ✅ (carried forward) |
| 20-22 | Engine Management, 39 engines, 0 disabled/degraded | `GET /v1/admin/engines/summary` → confirmed exact counts | ✅ |
| 23-24 | Vertical Configuration, Home Services enabled | `GET /v1/admin/verticals` → confirmed | ✅ |
| 25-26 | Audit Logs, auth/settings/engine/vertical events visible | `GET /v1/admin/audit-logs` (settings), `GET /v1/auth/audit-log` (auth) both confirmed with real entries | ✅ |
| 27-28 | Trigger 403, confirm request_id | `provider@serviceos.in` → `PUT /v1/admin/settings/...` → 403 with `request_id` | ✅ |
| 29 | No browser console errors | **Not verifiable** — no browser was ever opened | ❌ not run |
| 30 | No NaN/null/undefined in UI | **Not verifiable visually** — backend zero-state values confirmed as proper typed values (not `null`), which is the strongest available proxy, but not a substitute for actually looking at rendered DOM | ⚠️ partial |

## Bottom line

28 of 30 steps have strong evidence (API-level + SSR-level, several new
this sprint). Steps 29-30 genuinely require a browser and remain unverified.
Per the ticket's explicit rule — **"If manual smoke is skipped again, return
PARTIAL_READY_WITH_ADMIN_SETUP_BLOCKERS"** — this determines the final
recommendation. This sprint's smoke work is meaningfully more thorough than
Phase 0/1's (both servers were actually started and hit over real HTTP this
time), but it does not meet the bar of "real browser smoke" as literally
specified.
