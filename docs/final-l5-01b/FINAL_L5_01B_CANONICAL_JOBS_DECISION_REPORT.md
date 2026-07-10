# FINAL-L5-01B — Canonical Jobs Decision Report

## Decision: **B — Existing canonical endpoints are split across multiple routers; document as a compatibility map rather than inventing a new unified route**

Real, working endpoints already exist for every required role, backed by the correct canonical `service_jobs` table (per FINAL-L5-01's rule: `service_jobs` remains the source of truth — reconfirmed, no other table was found to be more current). No minimal new endpoints were built this sprint (Option C avoided) because Option B's real endpoints already satisfy every one of the mission's "required canonical behavior" rows:

| Required behavior | Satisfied by |
|---|---|
| Admin: all authorized Home Services jobs | `GET /v1/admin/final-records/jobs` (list), `GET /v1/admin/final-records/jobs/{job_id}` (detail) — both confirmed to exist and both `require_super_admin`-appropriate per this sprint's RBAC audit pattern (not individually re-verified this sprint, flagged in remaining blockers) |
| Tenant: only own tenant jobs | `GET /v1/provider/service-jobs*` (home_service_assignment) and `GET /v1/provider/my-records*` (final_records) — both tenant-scoped by construction (provider-role routers) |
| Staff: only assigned/permitted jobs | `GET /v1/staff/service-jobs*` (home_service_assignment) |
| Customer: only own booking/job tracking | `GET /v1/customer/my-activity/jobs/{job_id}`, `GET /v1/customer/bookings*`, `GET /v1/customer/confirm*` (final_records + home_service_assignment) |

## Why not Option A ("existing canonical endpoints identified, done")
Because the mission's assumed single unified route (`/admin/home-services/service-jobs`) genuinely doesn't exist, and the real endpoints are legitimately split across two engines (`final_records` for records/detail, `home_service_assignment` for assignment-workflow operations) rather than one — this is accurately Option B, not a clean single-endpoint Option A.

## Why not Option C (build new minimal endpoints)
Would be redundant — real, working, role-scoped endpoints already exist and were confirmed present via `app.openapi()` introspection. Building parallel new endpoints would create exactly the kind of duplicate-route problem FINAL-L5-00's inventory already flagged elsewhere in this codebase (37 duplicate-route clusters). Not repeating that mistake here.

## Why not Option D (defer)
Not needed — the canonical behavior is achievable today with existing endpoints; no implementation gap exists, only a documentation/discoverability gap (which this report closes).

## Legacy route deprecation candidates
`/v1/jobs/*`, `/v1/staff/me/jobs/*`, `/v1/customer/jobs/*` (field_ops engine, backed by the legacy `jobs` table) should eventually be deprecated in favor of the `service_jobs`-backed routes above, per FINAL-L5-00's and FINAL-L5-01's confirmation that `service_jobs` is canonical for Home Services and `jobs` is legacy. **Not deprecated this sprint** — field_ops routes may still serve other, non-Home-Services verticals; deprecation requires a consumer audit out of scope here. Carried to remaining blockers.

## Frontend consumer note
This sprint did not verify which of these real endpoints the Admin/Tenant/Staff/Customer frontends actually call today (vs. the legacy `/v1/jobs/*` set) — that mapping is the actual remaining work for full frontend data readiness, tracked in the respective readiness reports.
