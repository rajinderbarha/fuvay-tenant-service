# ADMIN-TENANT-E2E-04B — Usage Credit Ledger Link Report

**This is the ticket's primary blocker, now resolved.**

## What was built
1. Backend: `GET /v1/admin/tenants/{tenant_id}/usage-credit-ledger` now
   accepts an optional `job_id` query param, filtering server-side to
   the exact job's ledger entries (`app/engines/tenant_engine/admin_router.py`).
2. Frontend: `/admin/finance/usage-credits` now reads `?tenant_id=` and
   `?job_id=` from the URL (`useSearchParams`), pre-filling the tenant
   filter and passing `job_id` through to the API call — so navigating
   here with both params shows *only* that job's ledger entry, with a
   visible "Filtered by job: {id} — Clear filter" banner.
3. Frontend: the job detail page's Completed Job Deduction section links
   to `/admin/finance/usage-credits?tenant_id={tenant_id}&job_id={job_id}`.

## Browser-verified flow (Playwright, real Chrome)
1. Open `/admin/home-services/service-jobs/b035159a-b19b-4500-8cb4-99a412e8ac34`
   (JOB-20260710-000002, completed live this session).
2. Click "View exact entry in Usage Credit Ledger →".
3. URL changes to `/admin/finance/usage-credits?tenant_id=34b427a7-...&job_id=b035159a-...`.
4. Real API call observed: `GET /v1/admin/tenants/34b427a7-.../usage-credit-ledger?job_id=b035159a-...` → 200.
5. Exact ledger entry appears: `Completed Job Deduction`, `-21`, balance
   `3958 → 3937`.
6. Ledger entry's `job_id`/`booking_id` match the job/booking that was
   opened.
7. Balance arithmetic verified: `3958 - 21 = 3937` ✓ (matches the API's
   `balance_before`/`balance_after` exactly).
8. No duplicate — exactly 1 row shown, confirmed by both API
   (`count: 1`) and rendered table row count.

## Ledger arithmetic in context
Continuing this tenant's historical chain from E2E-04
(`4000 → 3979 → 3958`), this session's real completion extended it one
more real step: `3958 → 3937` (both ledger entries prior to this one
reference job_ids that no longer exist in the current `service_jobs`
table — stale from an earlier DB reset, documented in the source-of-truth
report — but the balance column itself is continuous and correct
regardless).

## Verdict
Full pass — the exact blocker E2E-04 could not resolve
("usage-credit-ledger link from that specific job could not be
browser-verified end-to-end") is now resolved, live, in a real browser,
for a genuinely freshly completed job.
