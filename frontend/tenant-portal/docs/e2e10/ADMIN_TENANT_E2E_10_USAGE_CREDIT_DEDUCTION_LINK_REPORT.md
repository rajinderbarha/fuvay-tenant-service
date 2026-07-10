# ADMIN-TENANT-E2E-10 — Usage Credit Deduction Link Report

## Static Analysis Only

## Usage Credit Deduction in Job Detail

### File: `app/(tenant)/jobs/[id]/page.tsx` (lines 278–290)
```jsx
{j.commission_amount != null && (
  <Card padding={20}>
    <h3>Usage Credit Deduction</h3>
    <div>
      <span>Completed Job Deduction</span>
      <span>{fmt(j.commission_amount)}</span>
    </div>
    <p>Provider usage credits are not real money and are not withdrawable.</p>
  </Card>
)}
```
- Appears after job financially closes (`commission_amount` field populated by backend)
- Clear disclaimer: credits are not real money, not withdrawable
- Does NOT show navigation link to ledger (minor UX gap — not a bug)

## Usage Credit Ledger Page

### File: `app/(tenant)/finance/usage-credit-ledger/page.tsx`
- Route: `/finance/usage-credit-ledger`
- Data source: `usageCreditsApi.getBalance()` + `usageCreditsApi.getLedger()`
- KPI cards: Balance, Credits Deducted, Completed Jobs count, Low Credit Status
- Table: date, job_id (truncated to 8 chars), event_type, credit_delta, balance_before, balance_after, reason, request_id
- `completed_job_deduction` event type rendered as "Completed Job Deduction" label ✓
- Error state with request ID displayed for debugging

## Cross-Link Assessment
- Job detail card shows deduction amount but NO direct link to `/finance/usage-credit-ledger`
- Navigation to ledger available via finance sidebar item
- UX recommendation (not a bug): add a "View Ledger →" link in the Usage Credit Deduction card

## Ledger Correctness
- `credit_delta < 0` = deduction, shown in `var(--danger-text)` (red)
- `credit_delta > 0` = credit added, shown in `var(--success)` (green)

## Status: FUNCTIONAL PASS (no cross-link, but not a blocker)
