# FINAL-L5-05B — Canonical Admin Jobs Migration Report

## Real feature-parity inventory (Part 2)
Full comparison performed between the legacy page (`/admin/operations`, backed by `jobsApi` → `/v1/jobs`, querying the separate `jobs` table via `app/engines/field_ops/`) and the canonical page (`/admin/home-services/service-jobs`, backed by `finalRecordsAdminApi` → `/v1/admin/final-records/jobs`, querying the real `service_jobs` table via `app/engines/final_records/`).

### Capabilities present in legacy, classified
| Capability | Legacy call | Canonical status | Classification |
|---|---|---|---|
| Reassign staff (list + detail) | `POST /v1/dispatch/jobs/{id}/reassign` | Missing entirely | `SUPPORTED_LEGACY_ONLY` |
| Override Status (admin transition bypass) | `PUT /v1/jobs/{id}/status` | Missing entirely | `SUPPORTED_LEGACY_ONLY` |
| Force Close | `POST /v1/jobs/{id}/close` | Missing entirely | `SUPPORTED_LEGACY_ONLY` |
| Void job | `POST /v1/jobs/{id}/void` (client method exists, unused even by the legacy UI) | Missing | `DEAD` on both sides — real backend capability, no UI anywhere |
| Add note / view notes | `POST`/`GET /v1/jobs/{id}/notes` (unused on legacy UI) | Canonical has a real, different, working notes endpoint (`GET /v1/admin/service-jobs/{id}/notes`) that **was dead code until this sprint** | `REQUIRES_BACKEND_CONTRACT_FIX` → **now `SUPPORTED_CANONICAL`, fixed this sprint** (read-only; no add-note UI exists on either page) |
| Status/assignment timeline | `GET /v1/jobs/{id}/timeline`, rendered on legacy detail | Canonical has 2 real, different, working timeline endpoints (`assignment-timeline`, `execution-timeline`) that **were dead code until this sprint** | **Now `SUPPORTED_CANONICAL`, fixed this sprint** |
| SLA tracking (breach/at-risk, SLA alert banner, SLA filter) | `jobsApi.slaAlerts()`, `sla_status` filter | No SLA concept in `service_jobs` model at all | `SUPPORTED_LEGACY_ONLY` — genuine backend gap, not a wiring gap |
| Ops summary stat cards | `GET /v1/jobs/admin/summary` | No equivalent | `SUPPORTED_LEGACY_ONLY` |
| 14-value status granularity (incl. rework/disputed/quality-check) | dropdown | Canonical only supports 5 coarse statuses | `SUPPORTED_LEGACY_ONLY` (narrower) |
| Working tenant/date filters | real, backend-honored | `assignment_status`/`created` are declared in the FE filter config but **`admin_list_jobs` in `app/engines/final_records/admin_router.py` doesn't read them** | `REQUIRES_BACKEND_CONTRACT_FIX` — not fixed this sprint |
| Staff/technician, revenue, city/zipcode, SLA columns | real table columns | Canonical list only shows Job#/Status/Assignment/Tenant(hidden)/Created | `SUPPORTED_LEGACY_ONLY` |

### Capabilities canonical has that legacy lacks
Completed Job Deduction ledger drill-down with duplicate detection, real booking/price/provider-snapshot relationship, completion-proof section, column manager/saved views, durable async export. All real, all preserved — this migration report does not propose removing any of them.

## Decision (Part 2 required outcome)
1. **Canonical Jobs list route**: `/admin/home-services/service-jobs` (once parity is closed).
2. **Canonical Jobs detail route**: `/admin/home-services/service-jobs/[jobId]` (once parity is closed).
3. **Create/action ownership**: mutation actions (reassign, status override, force-close, void) do not yet exist against `service_jobs` at all — they must be built (new backend endpoints + new UI), not simply "pointed" at from the canonical page, before the canonical page can safely become primary.
4. **Legacy redirect behavior**: `/admin/operations` keeps its existing real "legacy Field Ops" self-disclosure banner and its link to the canonical page (already present — verified via a new regression test) until migration is complete; it is NOT redirected away yet, because doing so today would silently remove reassign/override/force-close/SLA-tracking/summary-stats from admin users with no replacement.
5. **Removal/deprecation**: not scheduled this sprint — real replacement functionality must exist first (rule 5: "do not remove working job actions").

## What was fixed this sprint (real, live-verified)
Two backend endpoints (`assignment-timeline`, `execution-timeline`) and one endpoint (`notes`) already existed, were already correctly typed in `lib/api.ts` (`adminServiceJobAssignmentApi`, `adminExecutionApi`), and were **already proven working via live curl** (200, real JSON) — but were never called from any page (dead code). Wired into `/admin/home-services/service-jobs/[jobId]/page.tsx`'s new "Timeline & Notes" section. Live-verified: real Chromium test confirms the section renders with an honest empty state ("No timeline events recorded for this job.") for a job with no real timeline events yet, and the underlying API calls succeed (no error state, no 500).

## What remains a genuine, unclosed gap (Part 2's third allowed outcome: "document a real backend blocker")
Reassign, status override, force-close, void, SLA tracking, and summary stats have **no backend implementation at all** against `service_jobs`/`final_records` — this is not a wiring gap like the timeline/notes fix above, it is missing backend capability. Building real mutation endpoints (with permission checks, audit logging, and duplicate-submission protection per Part 5's requirements) for all 4 mutation actions, plus a summary-stats endpoint and SLA-tracking fields on the `service_jobs` model, is a substantial, multi-endpoint backend + frontend effort that was not safely achievable within this sprint's bounded scope without risking a shallow, unverified implementation of admin-critical job-management mutations.

## Result: primary "Jobs" nav item is NOT migrated this sprint
Migrating the sidebar's "Jobs" link to the canonical page today, before the missing mutation actions are built, would violate rule 5 ("do not remove working job actions") and rule 3 ("do not solve the Jobs defect by only replacing an endpoint string"). The honest, rule-compliant decision is to leave the primary Jobs nav item on `/admin/operations` (still `/v1/jobs`-backed) until real parity exists, documented here rather than forced through unsafely. This is the single largest remaining blocker for a clean `READY_FINAL_L5_05_ADMIN_INFORMATION_ARCHITECTURE_CERTIFIED` — see Remaining Blockers.
