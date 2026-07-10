# Phase 7B — Bug Fix Report

Three real bugs were discovered via live evidence-based smoke testing (curl against the real
running backend + real Postgres, authenticated as `staff@serviceos.in`) and fixed during this
sprint. A fourth "bug" investigated turned out to be a false alarm (display artifact).

## Bug 1 — `TENANT_SERVICE_AREA_READ` missing from staff/technician permissions (403)

**Symptom:** `GET /v1/tenant/service-areas` returned `403 PERMISSION_DENIED` for the real
technician account, even though the Phase 7B ticket explicitly requires a read-only Service
Areas page for technicians.

**Root cause:** `app/core/permissions.py`'s `ROLE_PERMISSIONS["staff"]` and `["technician"]`
lists never included `P.TENANT_SERVICE_AREA_READ`.

**Fix:** Added `P.TENANT_SERVICE_AREA_READ` to both the `"staff"` and `"technician"` permission
lists (mirroring the existing pattern where both keys are kept intentionally identical).

**Verification:** Live re-test after backend restart: `GET /v1/tenant/service-areas` →
`200 OK` with the real seeded area for Demo AC Services.

## Bug 2 — `provider_availability_rules` table missing (500)

**Symptom:** `GET /v1/provider/availability` returned a raw `500 INTERNAL_ERROR`.

**Root cause:** `app/engines/provider_portal/router.py`'s availability endpoints
(`GET/POST/PUT/DELETE /v1/provider/availability*`) query a `provider_availability_rules` table
that was never created by any migration — genuinely absent from the live database (confirmed
via `\dt`). Same class of bug as Phase 7's `provider_team_members` finding.

**Fix:** Added `alembic/versions/114_provider_availability_rules.py` (idempotent-guarded),
creating the table with the exact column set the router's INSERT/SELECT statements expect. Ran
`alembic upgrade head` against the live database.

**Verification:** Live re-test after migration: `GET /v1/provider/availability` → `200 OK`
with `{"rules": [], "count": 0}`.

## Bug 3 (design correction, not a backend bug) — Availability page must be read-only

While investigating Bug 2, found that `POST/PUT/DELETE /v1/provider/availability*` all require
`require_tenant_owner` — a technician can never create/edit/delete availability rules, only
list them. The original page draft included a create form that would have always failed with
403 for a real technician user. Corrected the page to be read-only (same pattern as the Service
Areas page), with copy directing the technician to their tenant admin for schedule changes.

## Bug 4 — `/v1/provider/activity` does not exist (404)

**Symptom:** `GET /v1/provider/activity` returned `404 NOT_FOUND`.

**Root cause:** No such endpoint exists anywhere in `app/engines/provider_portal/router.py` or
any other engine's non-admin routes. The only activity/audit endpoints in the codebase
(`security/router.py`'s `GET /activity` and `GET /audit-log`) are `require_super_admin`-gated.
This assumption was made in the initial `staffSelfApi.getActivity()` draft without verifying
the endpoint actually exists — caught by this sprint's live smoke-test discipline before
shipping. Note: `tenantSetupApi.getActivity` (a **pre-existing**, unrelated tenant-owner-facing
API method, not part of this sprint's 13 pages) also points at this same nonexistent endpoint —
flagged here for awareness but left unchanged as out of Phase 7B's scope (tenant-owner
dashboard, not the technician app).

**Fix:** Removed the fabricated `getActivity` call from `staffSelfApi`; the `/staff/activity`
page now shows an honest "not yet available" empty state instead of calling a nonexistent
endpoint. Documented as a remaining blocker.

## False alarm — apparent backslash-corrupted URL strings in `lib/api.ts`

During review, a `Read` tool output rendering appeared to show `authApi.login`/`updateMe` using
malformed strings like `"\v1\auth\login"` (invalid escape sequences that would not resolve to
`/v1/auth/login` at runtime). A direct `Grep` against the actual file content confirmed the real
file correctly contains `"/v1/auth/login"` and `"/v1/auth/me"` — the malformed appearance was a
rendering artifact in the conversation transcript, not a real defect in the file. No fix needed;
noted here only for audit completeness.
