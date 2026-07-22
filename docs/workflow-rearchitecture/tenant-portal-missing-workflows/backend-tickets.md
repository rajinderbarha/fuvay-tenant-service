# Tenant-Portal Missing Workflows — Backend Findings & Tickets

Investigation date: 2026-07-22. Branch: `design/ux-05-staff-technician-app`.
Scope: the 5 fixture-only showcase pages under `app/dev/ux-03` / `app/dev/ux-04`
in `frontend/tenant-portal`. For each, this doc records what real backend
support exists today (grepped directly against `app/engines/`, not assumed),
and what would need to be added before a real production page could replace
the showcase. No frontend page was built against data that doesn't exist.

## 1. Parts Approval / List queue — PARTIAL backend, ticket filed, page NOT built

Real, working endpoints exist, but only **scoped to a single job**:
- `POST /staff/jobs/{job_id}/parts-requests` — create (staff/tech)
- `GET  /staff/jobs/{job_id}/parts-requests` / `GET /provider/jobs/{job_id}/parts-requests` — list
- `POST /provider/jobs/{job_id}/parts-requests/{id}/approve|reject|install`
  (`app/engines/execution/home_service_router.py:248-346`, backed by
  `HomeServiceService.{create,list,approve,reject,install}_parts_request` in
  `app/engines/execution/home_service_service.py:357-492`)

There is **no cross-job listing endpoint** — `list_parts_requests()` always
takes a `job_id` and queries `PartsRequest.job_id == job_id`. A tenant-wide
"queue" page (the showcase's `parts-approval`/`parts-list`) would either need:
(a) a new endpoint `GET /provider/parts-requests?status=requested` querying
`PartsRequest` by `tenant_id` alone (trivial addition — the model already has
`tenant_id`), or (b) client-side N+1 (list jobs, then list parts per job),
which is not a real production pattern and was not built.

**Also flagging a correctness issue found while reading this code (not
fixed — backend change, out of scope for this frontend task):** the
approve/reject/**install** endpoints are all gated by
`require_staff_or_above_mutation`, whose docstring says it admits
`{super_admin, tenant_owner, staff, technician}`. That means a `technician`
role can currently call the parts **install** endpoint. This task's brief
states the canonical rule that only tenant_owner/provider may install/reject
parts, and technician must never gain that permission. This is a live
discrepancy between the stated canonical rule and the current backend guard
— worth a dedicated backend ticket (narrow the parts-approve/reject/install
routes to a technician-excluding dependency, mirroring
`require_owner_or_staff_mutation`'s pattern in `app/core/permissions.py:1015-1036`).

**TICKET-UX05-P1**: Add `GET /v1/provider/parts-requests` (tenant-scoped,
`status` + `job_id` optional filters, real pagination) to
`app/engines/execution/home_service_router.py` / `home_service_service.py`,
backed by a `PartsRequest.tenant_id ==` query with `job.job_number` joined in
for display. Until this exists, no real cross-job Parts queue page can be
built without an N+1 anti-pattern; none was built.

**TICKET-UX05-P2**: Restrict `provider_approve_parts_request` /
`provider_reject_parts_request` / `provider_install_parts_request` to
`tenant_owner`/`staff` only (exclude `technician`), consistent with the
canonical parts rule already stated in product docs.

## 2. Permission Editor — NO backend support, ticket filed, page NOT built

`app/engines/roles_permissions/admin_router.py` is explicit and
self-documenting: **RBAC is code-defined in `app/core/permissions.py`, not a
DB CRUD system.** `POST /roles`, `PUT /roles/{id}`, `/enable`, `/disable` all
return HTTP 501 `NOT_IMPLEMENTED` with that exact explanation. There is no
per-team-member permission-grant/deny table anywhere in `app/engines/` —
`list_permissions`/`list_permissions_grouped` are read-only enumerations of
the hardcoded `P` constants, and they are super_admin/platform-scoped
(`require_permission(P.PLATFORM_ROLES_READ)`), not tenant-team-member-scoped
at all.

This means the showcase's per-team-member grant/deny toggle editor has
**zero backend counterpart** — not partial, not read-only-adjacent. Building
even a read-only version would mean displaying nothing meaningfully
per-member (the only "permissions" data is the global, role-level constant
list, not what a specific staff/technician on this tenant currently has).
Per the task's own guidance (option 3b), no frontend page was built.

**TICKET-UX05-P3**: To support a real Permission Editor, a new
tenant-scoped table (e.g. `team_member_permission_overrides`: tenant_id,
user_id, permission_key, grant|deny, granted_by, created_at) plus
`GET/PUT /v1/provider/staff/{user_id}/permissions` endpoints in a tenant
router would be required, with deny-overrides-grant resolved at
`require_permission`-check time. This is a genuinely new capability, not a
wiring fix — sized as a multi-day backend + enforcement-layer change, not
attempted here.

## 3. Command Center — backend exists but is platform-wide (super_admin), not tenant-scoped

`app/engines/dashboard_command_center/service.py` is real and rich (executive
summary, health score, action queue, at-risk tenants, compliance/security,
engine health, etc.) — but every query is unscoped-by-tenant
(`SELECT COUNT(*) FROM tenants WHERE status = 'active'`, `FROM jobs` i.e. the
legacy field_ops table, `FROM commission_records`, etc.) and it is a
super-admin platform dashboard, out of this task's frontend scope (super-admin
frontend is explicitly excluded from this task, and building/reading it
further was intentionally not pursued past this identification).

There is no tenant-scoped equivalent composing dispatch + finance +
compliance into one queue for a single tenant. The individual pieces
(dispatch via `/provider/my-records/jobs`, finance via package/credit-ledger
endpoints, compliance via `provider/compliance`) are real and separately
wired into tenant-portal already, but no composite/aggregation endpoint
exists to back a single "Command Center" queue view without the frontend
doing an ad hoc multi-fetch merge — which is a legitimate composite-view
pattern (the task brief explicitly allows recombining already-real
per-domain data client-side), but was not attempted in this pass given
budget; flagged as the next actionable item.

**TICKET-UX05-P4** (lower priority / could be frontend-only): Build a
tenant-portal Command Center page that client-side merges the *already real*
`/provider/my-records/jobs` (open/at-risk), finance-package/credit-ledger
endpoints, and `/provider/compliance` endpoint into one action list — no new
backend endpoint strictly required, just composition. Not attempted this
pass; noted for a follow-up session.

## 4. SLA/Risk indicators — real computation exists server-side, but not exposed to tenant-portal

`app/engines/final_records/sla_summary.py` is real, tenant-scoped-capable,
and correctly uses the `service_jobs` pipeline (not field_ops): `compute_summary(db, tenant_id=...)`
returns `at_risk`/`breached`/`delayed` counts, and `attach_sla(db, jobs)`
computes per-job `sla_status` (`ON_TRACK`/`AT_RISK`/`BREACHED`) from
`PricingTier.default_sla_minutes` resolved via `TierLocation`. This is
exactly the data an SLA/Risk page needs.

However, this module is currently only wired into
`app/engines/final_records/admin_router.py`'s `/jobs/summary` (super-admin).
The tenant-facing `app/engines/final_records/provider_router.py`'s
`GET /jobs` does **not** call `attach_sla`/`compute_summary` — a tenant-portal
page has no real endpoint today from which to fetch SLA status per job or a
tenant-scoped SLA summary. Computing it client-side from raw `ServiceJob`
fields would require re-deriving `PricingTier`/`TierLocation` resolution in
the frontend, duplicating pricing logic the frontend has no legitimate access
to — that would be exactly the kind of fabrication this task prohibits, so no
page was built.

**TICKET-UX05-P5**: Wire `sla_summary.compute_summary`/`attach_sla` into
`final_records/provider_router.py`: add `GET /v1/provider/my-records/jobs/sla-summary`
(tenant-scoped `compute_summary`) and have `GET /jobs` optionally include
`sla_status`/`next_deadline` per item (reusing `attach_sla` on the already
resolved job list, same N+1-safe batching that exists today). Once either
lands, a real SLA/Risk tenant-portal page becomes straightforward to build on
top of the existing Jobs page pattern.

## 5. Operational Exceptions — REAL backend data existed, page BUILT

Unlike the other four, `ServiceJob` already stores everything this page
needs as real columns: `status` (includes `force_closed` and `voided`,
settable only via the admin override/force-close/void endpoints in
`home_service_router.py`) and `failure_reason` (free-text, when recorded).
The tenant-facing `GET /v1/provider/my-records/jobs?status=...`
(`final_records/provider_router.py:115`) already supports filtering by
status and is already wired into the tenant-portal API client
(`serviceJobsApi.list`, `lib/api.ts:2907`).

**Built**: `frontend/tenant-portal/app/(tenant)/operations/exceptions/page.tsx`
— fetches `force_closed` and `voided` jobs via the existing real
`serviceJobsApi.list({ status })`, merges/sorts them client-side, and
displays job number, exception kind, status, `failure_reason` ("Not
recorded" shown honestly when null — never fabricated), assigned staff
(short id, no fabricated name, consistent with the existing Jobs page
convention), and closed time. No "resolve" action exists on the page,
matching the showcase's own explicit non-goal ("NOT the blocked Booking
Exception Resolution engine"). Added to the sidebar under Operations as
"Operational Exceptions" (`lib/nav-config.ts`), route `/operations/exceptions`.

**Known limitation, stated honestly on the page itself**: `ServiceJob` has
only one `failure_reason` text column — there is no structured
escalation/owner/next-step model, so the page does not (and cannot,
honestly) offer escalation actions beyond linking to the job detail page.
A richer escalation workflow would need the same kind of data-model
investment as tickets P3/P4 above; not attempted here.
