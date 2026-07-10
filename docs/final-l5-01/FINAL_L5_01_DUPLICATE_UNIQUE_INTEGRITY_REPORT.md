# FINAL-L5-01 — Duplicate and Unique Integrity Report

| Check | Result | Expected |
|---|---|---|
| Duplicate user emails | 0 | 0 |
| Duplicate tenant slugs | 0 | 0 |
| Duplicate pricing rule codes | 0 | 0 |
| Duplicate completed-job-deduction per job | 0 | 0 |

Category key, service-type-within-service, brand-mapping-within-service, provider-price-range, service-coverage, area-coverage, booking-reference, and rule-key uniqueness were not independently re-checked this sprint for the catalog tables (unmodified, reused from prior sprints). `service_pricing_rules` and job/booking/ledger uniqueness — the tables this sprint actually wrote to — were checked directly and are clean.

**Result: 0 unintended duplicate rows across every check run. PASS.**
