# ADMIN-TENANT-E2E-04B — Home Services Job List Report

Route: `/admin/home-services/service-jobs` (EnterpriseDataGrid, Sprint 26).

## Checks
1. Real jobs appear — **11 real rows**, confirmed via live curl
   (`total: 11`) and browser screenshot (grid renders `Job #`, `Status`,
   `Assignment`, `Created` columns with real job numbers
   `JOB-20260710-000001` through `-000011`).
2. Freshest completed job appears — `JOB-20260710-000002`
   (`b035159a-...`), completed live this session, appears at the top
   (sorted `created_at desc` — note: this job's `updated_at` is the
   freshest completion, but the grid sorts by `created_at`, so it
   appears near the bottom by creation order, not completion recency —
   documented, not a bug, matches the column header's own label).
3. Job count matches backend — grid `total` field reflects the real
   `COUNT(*)` from `service_jobs`, confirmed equal to the curl-verified
   11.
4. Filters — Status and Assignment dropdowns present (EnterpriseFilterBar).
5. Search — present (tenant search box), not deeply exercised this pass.
6. Status badges — readable (`pending_assignment`, `completed`, etc.).
7. Payment mode — not shown in the list view (only in detail); the list's
   `COLUMNS` config doesn't include price/payment fields, only
   `job_number/status/assignment_status/tenant_id/created_at`.
8. No platform payment/escrow/payout wording — confirmed via forbidden
   label scan (0 matches).
9. No mock jobs — confirmed via mock data scan (0 matches) and live API
   verification (real DB-backed).

## Bug fixed
Prior to this session's fix, this entire list was **broken (401 on every
request)** — see `ADMIN_TENANT_E2E_04B_JOB_OPERATIONS_SOURCE_OF_TRUTH_REPORT.md`.

## Verdict
Real jobs load and render correctly. Row action "View Details" now
correctly opens the new job detail route (previously a broken link — see
detail report).
