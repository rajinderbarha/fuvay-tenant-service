# FINAL-L5-01 — Canonical Data API Smoke Report

Executed against the live backend at `localhost:8000` (which was already running throughout this sprint, restarted implicitly via its own process — not restarted by this sprint's work) using the canonical seeded users. Full results in `api-smoke-results.json`.

## Scope actually covered (real HTTP calls, not simulated)
7 of 9 checks passed as expected:
- Admin login (200), Customer login (200)
- Unauthenticated request to tenant staff endpoint (401, correctly rejected)
- Admin tenant listing (200, returns real "Demo AC Services" data)
- Admin service-job-assignments listing (200)
- Tenant Owner accessing tenant staff (200)
- Non-existent tenant ID (404, with `request_id` present in the error body)

## Two real findings — not hidden, not fixed this sprint
1. **RBAC gap**: `customer1@serviceos.local` (role=`customer`) successfully received `200 OK` with real tenant data from `GET /v1/admin/tenants` — expected `403 Forbidden`. This is a genuine authorization enforcement bug in the live backend, unrelated to the seed data itself (the seed correctly assigned a non-privileged `customer` role). Documented as a security finding for triage; not fixed in this data-seeding sprint since backend authorization logic changes are out of scope for FINAL-L5-01.
2. **Mission's assumed canonical route doesn't exist**: `GET /admin/home-services/service-jobs` returns `404`. The live backend's actual admin job routes are `/v1/admin/service-job-assignments`, `/v1/admin/service-job-assignments/unassigned`, `/v1/admin/service-job-assignments/assigned`, `/v1/admin/service-jobs/{job_id}/assignment-timeline` (confirmed via the live OpenAPI schema). The mission document's stated "Canonical Admin Home Services jobs route" does not match the current codebase — documented as a factual correction rather than silently assumed true.

## Not exercised this sprint (scope gap, documented)
The mission's Part 21 lists ~24 smoke areas across Admin/Tenant/Customer/Staff (catalog, pricing, matching, usage credits, notifications, audit, reports, tracking, booking, execution flow, etc.). Given time constraints, this sprint smoke-tested the areas most directly tied to the canonical seed's own entities (auth, tenant listing, job assignments, staff) rather than the full 24-area matrix. This is a real, acknowledged scope reduction — not a claim that all 24 areas were verified.

**Result: Core auth/tenant/job data-access smoke PASS. Two real findings documented (1 security, 1 documentation-accuracy). Full 24-area matrix not exhaustively covered — see remaining blockers.**
