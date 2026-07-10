# ADMIN-TENANT-E2E-04B — Remaining Blockers

## What was actually blocking E2E-04, discovered this pass
E2E-04 attributed its blocker to "two job systems, freshest job can't be
opened in one clean route." The real, deeper cause was worse and
different: the canonical route's own backend
(`app/engines/final_records/admin_router.py`, all 10 endpoints) was
**returning 401 for every admin, always** due to an auth
dependency-injection bug (`get_current_user(r)` called with a raw
`Request` instead of via `Depends`). This was never caught before because
it was likely verified via database inspection rather than a real
authenticated HTTP call. Fixed this pass — restart-verified live.

Additionally, the specific job E2E-04 called "freshest completed"
(`JOB-20260710-000001`) turned out to have no real completion record and
no ledger link at all — it was marked "completed" outside the real
completion flow at some earlier point. Rather than build a UI that fakes
a link for it, this sprint drove a real pending job through the actual
staff lifecycle live, producing a genuinely fresh, correctly-linked
completed job (`JOB-20260710-000002`) to browser-verify the full chain
against.

## Everything the ticket asked for, now real and browser-verified
1. Real Home Services jobs list — fixed (was 401, now 200, 11 rows).
2. Real job detail route — built new (`/admin/home-services/service-jobs/[jobId]`).
3. Service/lifecycle info — shown (status, assignment status, timestamps).
4. Provider, customer, service, price, payment mode — all shown, all real.
5. Completion status + proof — shown, real.
6. Completed Job Deduction info — shown, real (21 credits, 3958→3937).
7. Click-through to exact Usage Credit Ledger entry — built and
   browser-verified.
8. Exactly-once deduction — verified at two independent layers (state
   machine + ledger idempotency), live.
9. Zero mock data, zero forbidden labels — confirmed via scans.
10. Full browser verification via Playwright/real Chrome — 8/8 passing.

## Minor, non-blocking gaps (documented honestly, not fixed this pass —
out of "browser-only fix" scope or genuinely low-priority)
- No dedicated visual status timeline on the job detail page (the
  underlying `service_job_assignment_events`/`execution_events` admin
  endpoints exist but aren't wired into this page yet).
- Deduction section doesn't separately render the rule ID / idempotency
  key as distinct labeled fields (the raw `deduction_source` UUID is in
  the API response, just not broken out in the UI yet).
- The job list page's data-fetch still uses a raw inline `fetch()`
  instead of the central `apiFetch` client (pre-existing, unrelated to
  this sprint's blocker, not touched).
- `JOB-20260710-000001` (the original "freshest completed" job) remains
  in its pre-existing, deduction-less state — not retroactively fixed
  (there is no safe way to backfill a real deduction for a job that
  never went through the real flow); its detail page correctly shows an
  honest "no deduction record found" message rather than hiding the gap.

## Final certification decision

`READY_ADMIN_TENANT_E2E_04_ADMIN_MATCHING_OPERATIONS_DEDUCTION_CERTIFIED`

Every acceptance criterion in this ticket was met with real, live,
browser-verified evidence: the canonical job source of truth is resolved
and documented, its backend bug is fixed, a real job detail page exists
where none did before, the Completed Job Deduction section and Usage
Credit Ledger link both work end-to-end against a genuinely freshly
completed job, balance arithmetic is verified, exactly-once deduction is
verified at two layers, the legacy Operations board no longer misleads,
zero mock data / forbidden labels, TypeScript is clean, and Playwright
is 8/8 passing in a real browser. The remaining items are minor,
disclosed UI enhancements, not blockers.
