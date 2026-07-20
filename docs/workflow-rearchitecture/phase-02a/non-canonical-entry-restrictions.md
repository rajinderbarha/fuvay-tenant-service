# Non-Canonical UI Entry-Point Restrictions

## Status: NOT implemented this phase

None of Workstream 11's restrictions were applied:
- Legacy review-write UI blocking (`POST /v1/reviews`) — not touched, backend or frontend.
- Dead brands routes — not touched.
- Deprecated 410 workflows — not touched.
- Duplicate tenant-portal nav entries (`/provider/reviews`, `/provider/marketing`, `/provider/chat`, `/staff/home-services/jobs`) — not touched.
- Placeholder roles (`platform_admin`, `finance_admin`, etc. from `roles_permissions/service.py`) — not touched; these already render with an honest `is_implemented: false` badge per Phase 1A's finding, which was pre-existing, not a change made this phase.

## Why
None of these were required by, or adjacent to, the chosen technician My Work / Parts Request vertical slice. Applying them would have touched unrelated engines (`review`, `brands`, `package_commerce`) and unrelated frontend apps (super-admin, tenant-owner's Customers section) outside this phase's scope.

## Confirmed still safe to defer
Per `review-canonical-decision.md` (Phase 1A), the legacy `POST /v1/reviews` endpoint has zero confirmed frontend callers — deferring its blocking introduces no new risk beyond what was already true before this phase.
