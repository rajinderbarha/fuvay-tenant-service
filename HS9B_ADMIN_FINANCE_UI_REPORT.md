# HS9B — Admin Finance UI Report

## New page: `/admin/finance/usage-credits`
Real, new page — tenant-ID search box, summary mini-stats (ledger entry
count, total credits deducted, current balance from the ledger),
"Add Usage Credits" action (wired to the real, pre-existing
`POST /{tenant_id}/add-usage-credits` admin endpoint), and a full ledger
table matching most of the ticket's required columns (Date, Job ID,
Event Type, Credit Change, Balance Before, Balance After, Deduction
Source, Request ID — Tenant/Booking ID/Service/Type/Brand/Status/Actions
omitted, same "raw UUID, no human-readable join" limitation as the
tenant-facing page).

## Not implemented
- No cross-tenant "Total Usage Credits Deducted across all tenants" /
  "Tenants With Low Credits" / "Failed Deduction Events" summary — the
  page requires a specific `tenant_id` to be entered; there is no
  aggregate admin dashboard view (the backend has no cross-tenant
  endpoint to power one — see `HS9_ADMIN_FINANCE_VISIBILITY_REPORT.md`).
- `/admin/tenants/:tenant_id/usage-credits` (as its own sub-route) and
  `/admin/home-services/completed-job-deductions` (cross-tenant list)
  were not built — only the single search-based page above.
- "View Job" / "View Audit" row actions not wired (no per-row
  navigation target confirmed to exist yet).
- "Retry Failed Deduction" — not applicable, since deduction in this
  implementation cannot currently fail (see HS9's documented policy:
  always succeeds, even into negative balance).

## TypeScript
`npx tsc --noEmit` in `frontend/super-admin` → 0 errors (after fixing
one real signature mismatch: this codebase's `useAction` hook takes no
`onSuccess` option, unlike the tenant-portal's — the page was written
against the wrong hook signature initially and fixed to call
`ledger.refetch()` manually after a successful `execute()`).

## Verdict
Admin finance UI: **exists and works** for the per-tenant view. Not
`NOT_READY_HS9_FINANCE_UI_FAILED`. Cross-tenant aggregate views remain a
documented gap (no backend endpoint exists to power them yet).
