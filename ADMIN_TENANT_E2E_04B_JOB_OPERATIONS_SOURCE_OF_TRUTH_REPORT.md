# ADMIN-TENANT-E2E-04B — Job Operations Source of Truth Report

## Investigation

| Route | Backend endpoint | Table queried | Row count |
|---|---|---|---|
| `/admin/operations` | `GET /v1/jobs/admin/all` (`app/engines/field_ops/router.py:109`) | legacy `jobs` (Field Ops Engine, 23-status lifecycle) | 0 (empty in this dev DB) |
| `/admin/home-services/service-jobs` | `GET /v1/admin/final-records/jobs` (`app/engines/final_records/admin_router.py:102`) | `service_jobs` (Sprint 19 Final Records) | 11 real rows |

Both routes are linked from the sidebar (`Operations` under Operations
group, `Jobs` also present separately — see nav-config `operations` and
`home-services` sections).

## Real, live-breaking bug found and fixed this pass
`GET /v1/admin/final-records/jobs` — the canonical Home Services job
list endpoint — was returning a hard **401 `INVALID_TOKEN`** for every
admin, always, even with a valid `super_admin` JWT that worked fine on
every other admin endpoint. Root cause: every one of the 10 endpoints in
`app/engines/final_records/admin_router.py` called
`await get_current_user(r)` passing the raw FastAPI `Request` object
directly, instead of using the correct, established
`Depends(get_current_user)` dependency-injection pattern used everywhere
else in the codebase (confirmed via `app/engines/tenant_engine/admin_router.py`
and others). `get_current_user`'s `credentials` parameter is designed to
receive `HTTPAuthorizationCredentials` via `Depends(bearer_scheme)`, not
a `Request` — passing a `Request` object caused `decode_token()` to fail
on the wrong input type, which the broad exception handling in
`get_current_user` surfaced as `INVALID_TOKEN`.

**This means the entire "canonical" Home Services job/booking/
appointment/lead/audit-log/confirmation admin API module had never
actually worked over real HTTP for any admin**, despite E2E-04's earlier
claim of "11 real rows" (that claim was likely based on a database-level
check or a different, non-HTTP verification path, not a live authenticated
API call — this session confirmed it fresh with a real login + real
Bearer token).

## Fix applied
`app/engines/final_records/admin_router.py` — all 10 endpoints changed
from `await get_current_user(r)` to `user: UserContext =
Depends(get_current_user)` in the function signature (matching the
correct, established codebase pattern). Verified live after restart:
`GET /v1/admin/final-records/jobs` → 200, real 11 jobs returned.

## Decision: canonical source of truth

**Option C** (from the ticket's allowed solutions) — keep both routes,
clearly label them, ensure Home Services links go to the real route:
- `/admin/operations` = legacy Field Ops board (23-status lifecycle,
  genuinely empty in this dev environment — no legacy jobs were ever
  created). Now carries a persistent banner: *"This board shows Field
  Ops (legacy) jobs, a separate lifecycle from Home Services bookings…
  View real Home Services Jobs →"* linking to the canonical route.
- `/admin/home-services/service-jobs` = canonical Home Services job
  source of truth, now that its backing API actually works.

This was chosen over Option A/D (redirect/new route) because both
systems are real, distinct, intentional lifecycles (Field Ops vs Home
Services) — collapsing them would lose information, not add clarity.
Making the legacy page honest about what it is, and always one click
from the real data, resolves the "two confusing job systems" problem
without deleting a working (if currently-empty) module.

## Verdict
Source of truth resolved and documented. Root cause of the entire E2E-04
job-detail blocker found and fixed (not previously known — E2E-04
attributed the blocker only to "two systems," not to the canonical
system's own backend being broken).
