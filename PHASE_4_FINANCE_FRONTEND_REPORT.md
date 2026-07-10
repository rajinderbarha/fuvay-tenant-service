# Phase 4 — Finance Frontend Report

## Route mapping (real vs. ticket-assumed)

| Ticket assumed | Real route | Status |
|---|---|---|
| `/admin/packages` | `/admin/packages` | ✅ matches |
| `/admin/finance/usage-credits` | `/admin/finance/wallets` (+ `/admin/finance/topups`) | Real, different name — tenant wallet list/detail |
| `/admin/finance/security-deposits` | `/admin/finance/deposits` (+ `[deposit_id]`) | Real, different name |
| `/admin/finance/settings` | `/admin/settings` (generic settings engine, includes `finance_model`/plans) | Real, folded into generic Settings, not a standalone Finance Settings page |

All 4 real pages load, use real backend data, and were **not** rebuilt this
sprint (per the ticket's implicit scope — fix bugs in what exists, don't
duplicate). TypeScript: **0 errors** across the whole frontend after this
sprint's changes.

## Packages page (`/admin/packages`)

Confirmed via source inspection: full CRUD, 7 package-type tabs, summary
cards, create/edit modal with deposit/credits/staff-limit/service-area-limit
fields, Assigned Tenants and Audit Logs tabs. Fixed this sprint: the Audit
Logs tab was calling a field shape (`{logs, count}`) the (also newly-fixed)
backend endpoint doesn't return (`{items, total}`) — both the TS interface
and the tab's row-mapping were updated to match, and a Request ID column was
added to make the ticket's "audit rows show request_id" requirement visible.

## Provider Usage Credits (`/admin/finance/wallets` + `/admin/finance/topups`)

Tenant column already renders `tenant_name` as primary display (confirmed
via source: `row.tenant_name` — never a raw ID alone), satisfying the
ticket's explicit hard gate on this point. Balance/available/lifetime
fields are wired to the real `financeApi`/`adminWalletApi` clients calling
the real backend.

## Security Deposits (`/admin/finance/deposits` + `[deposit_id]`)

Full list/detail/approve/reject/refund/adjust UI already exists, wired to
`financeApi.listDeposits/getDepositsSummary/getDepositDetail/approveDeposit/
rejectDeposit/recordOfflineDeposit/refundDeposit/adjustDeposit`. This is a
**separate, more complete deposit workflow** than the `package_commerce`
mark-paid/refund/forfeit one documented in the backend report — both
operate on the same underlying `security_deposits` table. Not consolidated
this sprint (a genuine architecture decision, not a quick bug fix, and
outside this ticket's "certify + fix bugs" scope) — documented as a
carried-forward item.

## Finance Settings

No dedicated `/admin/finance/settings` page exists; the 4 required baseline
settings (`customer_pays_provider_directly`, `tenant_payouts_enabled`,
`job_credit_deduction_trigger`, `provider_usage_credits_enabled`) are real,
live-confirmed correct via the generic Settings engine
(`GET /v1/admin/settings`), editable through `/admin/settings` using
`settingsAdminApi`. Not a missing feature — a different, already-existing
home for the same capability.

## Forbidden label scan (frontend)

Zero matches for any of the 8 forbidden terms across
`app/admin/packages/page.tsx`, `app/admin/finance/wallets/page.tsx` (+ detail),
`app/admin/finance/deposits/page.tsx` (+ detail), `app/admin/finance/topups/page.tsx`,
`app/admin/finance/page.tsx`.

## Result: **Frontend certified.** TypeScript clean; real API integration confirmed; tenant name shown as primary display; one field-shape bug found and fixed (audit logs).
