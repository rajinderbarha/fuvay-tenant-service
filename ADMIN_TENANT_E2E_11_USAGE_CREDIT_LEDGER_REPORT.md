# ADMIN-TENANT-E2E-11 — Usage Credit Ledger Report

Route: `/finance/usage-credit-ledger`.

## Checks
1. Opens — 200, browser-verified.
2. Real ledger API called — `GET /v1/provider/usage-credits/ledger` → 200
   (network-logged in Playwright).
3. Completed Job Deduction entries appear — 3 real rows, all
   `event_type: completed_job_deduction`.
4. Balance math correct — verified for all 3 entries:
   `4000 - 21 = 3979`, `3979 - 21 = 3958`, `3958 - 21 = 3937`. All
   match `balance_before`/`balance_after` exactly.
5. Filters — not present on this page (no filter UI in source); not a
   defect per se, just a simpler page than the ticket's assumed column
   set — documented.
6. Search by job/booking — not present; job ID shown truncated
   (`entry.job_id.slice(0,8)`) as a column, not searchable.
7. No duplicate entries for same completed job — confirmed: 3 entries,
   3 distinct `job_id` values, no repeats.
8. No fake ledger rows — confirmed, real API-backed, matches E2E-04B's
   independently-verified admin-side ledger for the same tenant exactly.
9. No wallet wording — confirmed via forbidden-label scan.

## Columns actually present vs. ticket's expected set
Present: Date, Job ID, Event Type, Credit Change, Balance Before,
Balance After, Reason, Request ID — covers 7 of the ticket's 9 expected
columns (missing a distinct "Ledger ID" column — not shown, though
`entry.ledger_id` is used as the React key; and "Reference Type" isn't a
separate column since this ledger only has one reference type in
practice, `job_id`).

## Verdict
Full pass. Real data, correct arithmetic, no duplicates, no forbidden
wording.
