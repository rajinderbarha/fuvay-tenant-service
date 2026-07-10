# ADMIN-TENANT-E2E-05 — Completed Job Deductions (Finance-side) Report

Route: `/admin/home-services/completed-job-deduction` (`app/admin/home-services/completed-job-deduction/page.tsx`, 94 lines).

## What it actually is
A **rule configuration view**, not a transaction log — it lists which service/type/brand combinations trigger an automatic usage-credit deduction on job completion, and how many credits each deducts. This is deliberately separate from the ledger (which shows what already happened) and from `/admin/finance/usage-credits` (which shows a tenant's running balance).

## Real-data verification
- Demo rule confirmed present and correct: AC Repair / Split AC / LG → **21 usage credits** per completed job.
- Playwright evidence (this session, fresh run): body text contains both "Completed Job Deduction" and "21 usage credits" — `frontend/e2e-admin-tenant/evidence/e2e05/completed-job-deduction.log` / `.png`.
- Cross-checked against the DB: both real `usage_credit_ledger` rows for this tenant use exactly `credit_delta=-21.00` against an AC-Repair/Split-AC/LG job, matching the configured rule (no drift between config and what has actually fired).

## Isolation from the finance route naming trap
This is the **real** deduction-config route. `/admin/finance/wallets` is a different, legacy balance system (see Route Verification + Baseline Data reports) and does not duplicate or conflict with this page's rule data.

## Verdict: PASS — real rule engine view, correctly reflects the 21-credit AC-Repair rule, consistent with actual fired ledger rows.
