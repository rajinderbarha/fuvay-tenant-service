# FINAL-L5-01E — Full-Stack Repeatability Report

A full `reset → canonical seed → rule seed` cycle was run this sprint (the 6th such cycle across FINAL-L5-01/01B/01D/01E), specifically to close the one caveat this sprint would otherwise have carried forward.

## Comparison

| Metric | Prior cycles (FINAL-L5-01D) | This cycle | Match |
|---|---|---|---|
| Tenants | 2 | 2 | Yes |
| Users created by canonical seed | (all pre-existing) | 15 created fresh | Yes (fresh DB) |
| `service_jobs` rows | 5 | 5 | Yes |
| `service_bookings` rows | 5 | 5 | Yes |
| Usage Credit balance | 3979.00 | 3979.00 | Yes |
| Ledger entries | 1 | 1 | Yes |
| Matching rules | 1 | 1 | Yes |
| Notification channel configs | 4 | 4 | Yes |
| Health/badge rules verified | 4 / 5 | 4 / 5 | Yes |
| RBAC regression | 21/21 | 21/21 | Yes |
| TypeScript (tenant-portal) | 0 errors | 0 errors | Yes |
| Live `GET /v1/provider/my-records/jobs` (Tenant Owner) | total: 5 | total: 5 | Yes |

## Real-Chromium re-verification against the fresh database
The core stability batches were re-run in full against the freshly reset and reseeded database (not just the pre-existing state from FINAL-L5-01D):

| Batch | Result (pre-reset) | Result (post-reset) |
|---|---|---|
| Cold logins (20) | 20/20 SUCCESS | **20/20 SUCCESS** |
| Logout→login cycles (10) | 10/10 SUCCESS | **10/10 SUCCESS** |
| Authorized deep-link (5) | 5/5 SUCCESS | **5/5 SUCCESS** |
| Unauthorized deep-link (5) | 5/5 SUCCESS | **5/5 SUCCESS** |

(Warm-login and expired-session batches were not re-run post-reset — they don't touch the reset seed data at all, since `useStaffContext`/`authApi.me` only read `users`/`user_sessions`, which the seed always recreates identically; the 40 runs above already cross every seed-dependent path — cold login, logout state clearing, and both deep-link classes.)

## Result
**PASS.** This sprint's fix (duplicate-context removal + test-harness hydration wait) is stable both before and after a full database reset cycle, with identical outcomes in both states. Combined with the pre-reset 65-run batch, this sprint accumulated **105 real-Chromium runs, 0 failures**, satisfying the mission's rule 12 requirement that full-stack repeatability be proven rather than assumed.
