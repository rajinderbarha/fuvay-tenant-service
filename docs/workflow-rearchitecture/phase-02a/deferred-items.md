# Deferred Items

Everything below is specified in the Phase 2A brief and Phase 1A decisions but was **not** implemented this phase, in favor of a single fully-working vertical slice. None of it was started, stubbed, or partially wired — deferred cleanly for a future phase to pick up against the same Phase 1A source of truth.

## Workstream 1 — Navigation and route reconciliation
- Super-admin nav/route drift fix (~10 orphaned pages)
- Tenant-owner duplicate nav entry removal (`/provider/reviews`, `/provider/marketing`, `/provider/chat`)
- `/staff/home-services/jobs` duplicate retirement
- Redirects for any RETIRE-disposition route
- 403 handling additions beyond what already exists

## Workstream 2 — Role-specific navigation shells
- Super_admin, admin_operations/finance/security/readonly shell (9 items)
- Tenant_owner shell (9 items)
- Staff/manager shell (7 items, distinct from technician)

## Workstream 3/4 — My Work
- Admin, tenant_owner, staff-role My Work sources and pages (only technician built)
- Saved views, search, SLA filter, priority filter UI

## Workstream 5 — Next-action foundation
- Reusable backend/frontend contract and panel — not built for any of the 8 domains (see `next-action-implementation.md` for rationale)

## Workstream 6/8 — Page consolidation
- Business 360 container
- Provider/tenant business workspace container
- Finance Home, Reporting merge, Setup Wizard, Governance Console, Staff Profile consolidation

## Workstream 7 — Provider Home foundation
- Not built (tenant_owner Home is untouched this phase)

## Workstream 6 (Admin Home foundation)
- Not built (super-admin Home is untouched this phase)

## Workstream 9 — Advanced-page relocation
- No pages moved

## Workstream 11 — Non-canonical UI entry restrictions
- Legacy review-write blocking
- Dead brands route hiding
- Placeholder-role exclusion (already honest, unchanged)
- Duplicate nav entry removal

## Workstream 12 — Aggregation endpoints
- Admin home summary
- Business approval summary
- Provider setup progress
- Business/provider 360 summary

## Booking Exception Resolution
Correctly not implemented, per the non-negotiable rule — remains BLOCKED per `booking-job-canonical-decision.md` pending the backend investigation into whether `Booking`/field_ops `Job` and `ServiceJob` cover the same real-world bookings.

## Recommended next slice
Given this phase proved the technician My Work + Parts Request pattern works end-to-end, the most natural next vertical slice is the **tenant_owner** equivalent: a tenant_owner My Work endpoint/page (sources: business setup incomplete, verification changes requested, service/pricing/coverage/team setup incomplete, package/credit attention, document expiry) — reusing the same derivation pattern (real records, no new state table, honest `sources_unavailable` reporting) established in `app/engines/execution/my_work_service.py`.
