# FINAL-L5-01 — Foreign-Key and Orphan Integrity Report

All checks run directly against the post-seed, post-second-run database. Results in `data-integrity-results.json`.

| Check | Result | Expected |
|---|---|---|
| Tenant-role users without a valid tenant | 0 | 0 |
| Service types without a valid category | 0 | 0 |
| Bookings without a valid customer | 0 | 0 |
| Service jobs without a valid booking | 0 | 0 |
| Service jobs without a valid tenant | 0 | 0 |
| Ledger entries without a valid tenant | 0 | 0 |
| Completed-job-deduction ledger entries without a valid job | 0 | 0 |
| Notifications without a valid user | 0 | 0 |
| Job assignments referencing a technician from the wrong tenant | 0 | 0 |

Brands/issues-without-service-association, provider-ranges-without-admin-rules, and coverage-without-valid-associations were not independently re-checked this sprint since those catalog structures were not modified (reused as-is from prior sprints, already validated in earlier certification sprints per the FINAL-L5-00 database inventory).

**Result: 0 unexplained orphan records across every check run. PASS.**
