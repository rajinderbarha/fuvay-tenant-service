# HS9B — Tenant Finance UI Report

## Bug found and fixed
`frontend/tenant-portal/app/(tenant)/finance/usage-credit-ledger/page.tsx`
already existed with a real, complete UI shell (summary cards, ledger
table, loading/empty/error states) but called
`tenantSetupApi.getLedger()` → `GET /v1/provider/wallet/ledger` — a
**Sprint 23 "wallet" endpoint**, a completely different, pre-existing
invoice/commission concept, unrelated to Home Services usage credits.
The page's own built-in fallback copy ("Usage Credit Ledger endpoint
unavailable...") confirms this route never actually worked for its
stated purpose.

Fixed: added a real `usageCreditsApi` client
(`GET /v1/provider/usage-credits/balance`, `GET
/v1/provider/usage-credits/ledger` — both built and live-verified in
HS9/HS9B) and rewired this page to it. Did **not** touch, rename, or
rebuild the Sprint 23 wallet system itself — out of scope per the
ticket's explicit instruction.

## Result
- Title/subtitle match the ticket exactly ("Usage Credits" /
  "Track your Home Services usage credit balance, completed job
  deductions, and credit activity.").
- Summary cards: Usage Credit Balance, Credits Deducted, Completed
  Jobs, Low Credit Status (4 of the ticket's 5 — "Last Deduction" shown
  as inline text below the cards instead of its own card, for layout
  reasons).
- Ledger table columns match the ticket's required set: Date, Job ID,
  Event Type, Credit Change, Balance Before, Balance After, Reason,
  Request ID (Booking ID/Service/Type/Brand columns omitted — the
  ledger entries returned by the backend don't carry those fields
  today, only `service_id`/`service_type_id`/`brand_id` as raw UUIDs,
  not human-readable names — documented as a gap, not fabricated with
  fake labels).
- Error state shows the ticket's exact copy and `request_id`.
- Correct event label: "Completed Job Deduction" (mapped from the raw
  `completed_job_deduction` event_type).

## Not implemented
- `/tenant/operations/jobs/:job_id` finance section (Selected Price /
  Collected Amount / Completed Job Deduction / Ledger Entry inline on
  the job detail page) — HS8B's job detail page already shows
  Completion Proof (work summary + collected amount); it does not show
  the deduction credits or link to the specific ledger row for that job.
  Not added this pass.
- `/tenant/finance` (a parent finance landing page) — the pre-existing
  `finance/page.tsx` was not audited or updated this pass.

## TypeScript
`npx tsc --noEmit` → 0 errors.

## Verdict
Tenant finance UI: **exists and now works** (real bug fixed). Not
`NOT_READY_HS9_FINANCE_UI_FAILED`. Job-detail-level integration remains
a documented gap.
