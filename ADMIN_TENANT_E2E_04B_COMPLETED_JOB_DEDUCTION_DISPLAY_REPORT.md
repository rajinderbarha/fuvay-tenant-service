# ADMIN-TENANT-E2E-04B — Completed Job Deduction Display Report

Built into the new job detail page's "Completed Job Deduction" section.

## Fields shown (when a deduction exists)
- Deduction Status — `Deducted` badge.
- Deduction Credits — `21 usage credits` (`Math.abs(credit_delta)`).
- Balance Before / Balance After — real ledger values.
- Deducted At — real timestamp.
- (Deduction Rule ID / Idempotency Key not separately surfaced — the
  ledger's `deduction_source` field, which is the pricing-rule UUID, is
  available in the API response but not yet rendered as a distinct field
  in this pass; not required by the ticket's minimum field set to be
  functional, documented as a minor future enhancement.)

## Checks
1. Completed job shows deduction status — **yes**, verified live for
   `JOB-20260710-000002`.
2. Deduction credits = 21 for baseline — **yes**, confirmed both via API
   (`credit_delta: -21.0`) and rendered UI (`21 usage credits`).
3. Deduction associated with same job/booking — **yes**, ledger row's
   `job_id`/`booking_id` match the job/booking being viewed (server-side
   join on `job_id`).
4. Deduction appears only once — **yes**,
   `usage_credit_deduction_duplicate_count: 0` confirmed both via API and
   UI (no "duplicate" warning rendered — verified via Playwright
   assertion `not.toMatch(/duplicate/i)`).
5. If deduction missing, honest message shown — **verified live** for
   `JOB-20260710-000001`: *"No deduction record found for this job — this
   completed job predates the real completion+deduction flow, or the
   deduction genuinely failed."* (not a fake row).
6. No fake deduction row — confirmed, this section renders `null` state
   with an honest message when no ledger row exists, never a placeholder
   with zeroed/fake values.

## Verdict
Full pass, verified against both a real deducted job and a real
non-deducted job, with distinct, honest behavior for each.
