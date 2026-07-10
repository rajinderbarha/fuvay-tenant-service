# ADMIN-TENANT-E2E-04B — Browser Evidence Report

All evidence real, captured from real system Chrome runs this session,
saved under `frontend/e2e-admin-tenant/evidence/e2e04b/`.

| # | Route | Action | API observed | Data shown | Screenshot | Errors | Result |
|---|---|---|---|---|---|---|---|
| 1 | `/admin/home-services/service-jobs` | Load | `GET /v1/admin/final-records/jobs` → 200 (was 401 before this session's fix) | 11 real jobs | `job-list.png` | none | PASS |
| 2 | (fresh completed job row) | Identify | n/a | `JOB-20260710-000002`, completed live this session | — | none | PASS |
| 3 | `/admin/home-services/service-jobs/{id}` | Open detail | `GET /v1/admin/final-records/jobs/{id}` → 200 | Full sections: Job Summary, Service Details (₹850, Customer Pays Provider Directly), Completion (real work summary), Customer, Provider (Demo AC Services), Booking | `job-detail.png` | none | PASS |
| 4 | (same page) | View deduction | (same call, enriched) | Completed Job Deduction: 21 credits, 3958→3937 | `job-detail-deduction.png` | none | PASS |
| 5 | Click ledger link | Navigate | `GET /v1/admin/tenants/{tid}/usage-credit-ledger?job_id={id}` → 200 | Filtered ledger, 1 entry, exact job_id | `ledger-filtered.png` | none | PASS |
| 6 | (same page) | Verify math | (same call) | `1 LEDGER ENTRIES`, `21 TOTAL DEDUCTED`, `3937 CURRENT BALANCE` — table row `-21, 3958, 3937` | `ledger-filtered.png` | none | PASS |
| 7 | `/admin/operations` | Load bridge | `GET /v1/jobs/admin/all` → 200 | Honest empty legacy board + bridge banner | `legacy-operations-bridge.png` | none | PASS |

## Verdict
Real, literal browser evidence for the entire chain this ticket asked
for: job list → job detail → deduction section → ledger link click →
exact filtered ledger entry → verified balance arithmetic. This is the
first session where this full chain has been demonstrated end-to-end in
a real browser with a genuinely, freshly completed job.
