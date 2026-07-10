# ADMIN-TENANT-E2E-11 — Completed Job Deduction Ledger Report

## Checks
1. At least one `completed_job_deduction` entry exists — **yes, 3**
   (real, not a test fixture created this pass — the freshest one was
   produced live during E2E-04B by driving `JOB-20260710-000002` through
   the real staff completion flow).
2. Deduction amount correct — `-21` credits per entry, matches the
   platform's configured Completed Job Deduction rule (established
   across the whole session).
3. `balance_before - deduction = balance_after` — verified for all 3:
   `4000-21=3979`, `3979-21=3958`, `3958-21=3937`.
4. Ledger entry references job/booking — confirmed, `job_id` present
   and correct on all entries (`b035159a-...` for the freshest one,
   matching the admin-side job detail built in E2E-04B).
5. Job detail can link to ledger — **not applicable on the tenant side**
   this ticket covers (tenant has no per-job detail page with a
   deduction card in this sprint's scope — that's the admin-side
   surface, already built/fixed in E2E-04B). The tenant ledger page
   itself is the destination, not a link target from a job page.
6. Known E2E-10 gap ("no cross-link from job detail's Usage Credit
   Deduction card to the ledger") — this gap is about the **tenant Jobs
   module**, explicitly out of this ticket's scope
   ("Tenant jobs certification" excluded). Not re-verified or fixed
   here; carried forward as documented in E2E-10, unchanged.
7. Deduction not duplicated — confirmed, 3 entries for 3 distinct real
   completions, no repeats for the same job.

## Verdict
Full pass on everything in this ticket's actual scope (the ledger
itself). The known cross-link gap is a tenant-Jobs-module concern,
correctly out of scope here and left for whichever sprint covers tenant
Jobs next.
