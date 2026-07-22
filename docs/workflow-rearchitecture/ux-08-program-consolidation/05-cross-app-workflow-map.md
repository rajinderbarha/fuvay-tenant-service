# UX-08 Workstream 6: Cross-App Workflow Map

Status: CONSOLIDATED-FROM-PRIOR-EVIDENCE, with a fresh, honest attempt at
DB re-verification this pass that came back ENVIRONMENT_BLOCKED (documented
below, not glossed over).

## DB re-verification attempt (fresh this pass)

Per the brief, attempted a couple of real, read-only `SELECT` queries
against `localhost:5432` to re-confirm the Round 3 booking/job/review chain
is still consistent. Checked for tooling first:

- `psql` binary: not present in this environment's PATH.
- `python3 -c "import psycopg2"` / `import asyncpg`: neither driver
  installed.
- `docker ps`: Docker Desktop's engine pipe is not reachable
  (`failed to connect to the docker API at
  npipe:////./pipe/dockerDesktopLinuxEngine`).
- Direct TCP probe: `timeout 3 bash -c "echo > /dev/tcp/localhost/5432"` ->
  connection failed, port unreachable from this worktree's shell
  environment.

**Result: ENVIRONMENT_BLOCKED.** The backend/database is not reachable from
this UX-08 worktree's shell this pass — consistent with the same kind of
environment gap noted at the end of UX-07 Pass 3f ("backend unreachable in
this worktree"). Not worked around by fabricating a query result — the
booking/job/review chain below is reported exactly as it was documented by
the prior round that had live backend access, cited, not re-verified.

## Booking -> Job -> Completion -> Review -> Commission chain (UX-07 Round 3, cited verbatim, not re-derived)

Source:
`docs/workflow-rearchitecture/ux-07-cross-app-production-readiness/cross-app-workflow-map.md`
and
`.../completion-commission-review-verification.md`, both read in full this
pass.

```
customer (mobile/customer-app)
  -> POST .../booking-drafts ... -> POST .../confirm
  -> creates ServiceBooking (BK-20260721-000008) + ServiceJob (JOB-20260721-000008)
       |
       v
tenant_owner (tenant-portal, tenant 5209ef33-...)
  -> GET /v1/provider/service-jobs/assignable   (sees the same job)
  -> GET .../eligible-staff -> POST .../assign  (assigns real technician)
       |
       v
technician (mobile/staff-app, same tenant)
  -> GET /v1/staff/service-jobs                 (sees the same job, assigned)
  -> POST .../accept                            (real, legal status transition)
       |
       v
technician -> POST /v1/staff/service-jobs/{id}/complete
  {work_summary:"AC gas refilled and unit tested - UX07 Round 3 E2E completion",
   collected_amount:775.0, payment_mode:"customer_pays_provider_directly"}
  -> status:"completed"
       |
       v
server-side usage-credit deduction (real, never client-calculated):
  ledger_id: 846951c7-7446-4e46-aa9e-8d9ac3fb2898
  event_type: completed_job_deduction
  credit_delta: -21.0 (balance 3980.0 -> 3959.0)
  deduction_source: c6dd09d3-187b-4a99-beec-2e66f6751edf (ServicePricingRule id)
       |
       v
customer -> GET /v1/customer/reviews/eligibility?record_type=service_job&record_id={job_id}
  -> {eligible:true, record:{status:"completed", ...}}
customer -> POST /v1/customer/reviews
  {tenant_id, record_type:"service_job", record_id, overall_rating, ...}
  -> review_number: REV-56700400, status:"pending", visibility:"private_until_approved"
provider -> GET /v1/provider/reviews -> same review_number visible, correctly still "pending"
```

Identity is preserved across all 3 apps for a single real
ServiceBooking/ServiceJob pair on the canonical Home Services pipeline
(ServiceBooking -> ServiceJob) — no adaptation into the legacy `field_ops.Job`
model at any hop.

## Earlier UX-06 bookings (cited, not re-verified this pass)

Per user memory (`project_ux05_backlog_bl001.md` / repo history) and UX-06's
own closure docs, `BK-20260721-000005` and `BK-20260721-000006` were the
earlier UX-06-era customer bookings exercised before the Round 3 chain
above existed. Cited here as pre-existing data-continuity evidence, not
re-queried (DB unreachable this pass, as documented above).

## Real defects surfaced by this chain (cited, still open)

1. **`POST /v1/customer/reviews` 500-on-misnamed-field defect** — passing
   plausible-but-wrong field names (`rating`, `score`, `comment` instead of
   the real `overall_rating`/`review_title`/`review_text`) crashes with a
   raw, unhandled `500 INTERNAL_ERROR` instead of a structured `422`
   validation error. Root cause (per the cited doc): direct
   `body["tenant_id"]` / `int(body["overall_rating"])` dictionary access in
   `app/engines/customer_reviews/customer_router.py:32-60` with no
   try/except around the `KeyError`. Backend-owned, not fixed by any UX
   round to date. Carried forward into this pass's Workstream 12-13
   registry (doc 07) as `TICKET-UX08-002`.
2. **`mobile/customer-app`'s `ReviewScreen.tsx` still not wired to the real
   `POST /v1/customer/reviews` endpoint** discovered in UX-07 Round 3 — the
   screen still shows "Review submission isn't available yet" rather than
   using the now-confirmed-real endpoint. This is explicitly flagged in the
   cited doc as "the single highest-value, most concrete 'ready to
   implement' finding" from UX-07 Round 3, deliberately left unimplemented
   pending a dedicated follow-up. Per the UX-08 brief (no new code
   features), this is **not** implemented in this pass either — it remains
   an open, well-documented frontend task, carried into doc 07 as
   `TICKET-UX08-003` (frontend-only, no backend dependency, contract
   already fully known).

## Workstreams NOT re-attempted this pass (per brief's lighter-weight guidance)

- Super-admin's view of this same tenant/job — UX-07 Round 1 explicitly
  noted no super_admin credential was available that round; not
  re-attempted here (DB/backend unreachable, see above, makes any live
  credential check moot this pass regardless).
- Tenant onboarding, catalog/pricing continuity, error/recovery-state
  workflows — out of scope for this consolidation pass; still an open gap
  inherited from UX-07, not newly discovered.
