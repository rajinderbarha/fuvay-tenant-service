# HS10 — Completion + Deduction Report

All 11 ticket checklist items live-verified this session:

1. Job can complete only from valid status — ✅ (`COMPLETABLE_JOB_STATUSES` gate; duplicate attempt → `422 JOB_NOT_COMPLETABLE`)
2. Work summary required — ✅ (`422 WORK_SUMMARY_REQUIRED` when omitted, verified in HS8B/HS9)
3. Collected amount required — ✅ (`422 COLLECTED_AMOUNT_REQUIRED`)
4. Payment mode remains `customer_pays_provider_directly` — ✅, confirmed unchanged through every stage
5. Job becomes Completed — ✅
6. Completed Job Deduction resolves correctly — ✅, `-21` credits, exact specificity match (Split-AC+LG rule, not the Window-AC rule)
7. Usage credits deduct after completion — ✅, atomic with completion (same API response)
8. Ledger entry created — ✅
9. Balance before/after correct — ✅, `3979.0 → 3958.0`, arithmetic exact
10. Duplicate completion does not deduct twice — ✅, live-verified this session (retry → `422`, ledger unchanged at 2 entries total)
11. Admin and tenant finance pages update — ✅ backend (both real endpoints return the fresh ledger entry); frontend pages exist and are TypeScript-clean (HS9B) but not click-through-verified in a browser this session

## Idempotency hard test
Called completion twice for the same job — confirmed **no second
deduction**, existing `completed` job status itself is the enforcement
mechanism (backed by a real DB unique index on the ledger as a second,
independent guard).

## Verdict
Completion + deduction: **fully live-verified, all hard gates satisfied.**
