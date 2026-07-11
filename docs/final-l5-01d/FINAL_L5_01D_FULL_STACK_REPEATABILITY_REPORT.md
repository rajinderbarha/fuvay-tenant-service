# FINAL-L5-01D — Full-Stack Repeatability Report

A full `reset → canonical seed → rule seed` cycle was run after this sprint's fixes (the 5th such cycle across FINAL-L5-01/01B/01D).

## Comparison

| Metric | Prior cycles | This cycle | Match |
|---|---|---|---|
| Migration head | 131 | 131 | Yes |
| Tenants | 2 | 2 | Yes |
| `service_jobs` rows | 5 | 5 | Yes |
| `service_bookings` rows | (0 before this sprint's fix) | **5** | Yes — new, correct, stable |
| `service_jobs.booking_id` correctly linked to `service_bookings.id` | N/A before fix | **5/5** | Yes |
| Usage Credit balance | 3979.00 | 3979.00 | Yes |
| Ledger entries | 1 | 1 | Yes |
| Matching rules | 1 | 1 | Yes |
| Notification channel configs | 4 | 4 | Yes |
| RBAC regression | 21/21 | 21/21 | Yes |
| TypeScript (tenant-portal) | 0 errors | 0 errors | Yes |
| Live `GET /v1/provider/my-records/jobs` (Tenant Owner) | total: 5 | total: 5 | Yes |
| Live `GET /v1/customer/bookings` (Customer One) | items: 5 | items: 5 | Yes |
| Duplicate booking projections | 0 | 0 | Yes |
| Manual repair required | No | No | Yes |

## Result
**PASS.** Both this sprint's primary fixes (Tenant Jobs canonical migration, Customer Booking source alignment) are proven stable across a full reset cycle, not just a one-off state. Tenant Jobs page works on both runs (verified live pre- and post-reset). Customer bookings page works on both runs (verified live pre- and post-reset).

## Not covered by this repeatability cycle
Tenant Read Only browser precision and Technician redirect were **not** re-run through a second full browser-test cycle this pass (time constraint) — their fixes are code-level and don't depend on seed state, so a DB-reset cycle doesn't meaningfully re-test them; a second *browser* cycle specifically for those two would be the more relevant repeatability test, not performed given time constraints.
