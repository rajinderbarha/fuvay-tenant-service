# ADMIN-TENANT-E2E-10 — Forbidden Label Scan

## Static Analysis Only

## Forbidden Labels Checked
1. Cash Wallet
2. Wallet Balance
3. Withdraw (financial context)
4. Withdrawable (financial context)
5. Escrow
6. Provider Cash Balance
7. Credit Wallet Health
8. Bargain (as UI label)

## Scan Scope
`app/(tenant)/` all .tsx files

## Results

### Cash Wallet
**Not found** anywhere in tenant portal.

### Wallet Balance
**Not found** as a UI label. `packages/page.tsx` uses "Wallet" (acceptable) and "Available" as card headings.

### Withdraw (financial)
Occurrences found in `account/privacy/page.tsx` and `provider/compliance/page.tsx` — all are **consent withdrawal** labels ("Withdraw Consent", "Consent Withdrawal"), NOT financial withdrawal. ✓ Acceptable.

### Withdrawable (financial)
Found in:
- `account/privacy/page.tsx` — `const WITHDRAWABLE = new Set(...)` — this is a set of withdrawable consent types, not financial. ✓ Acceptable.
- `jobs/[id]/page.tsx` (line 287 and 561) — text: **"Provider usage credits are not real money and are not withdrawable."** This is an explicit disclaimer that credits are NOT withdrawable — the negative form is correct and expected. ✓ Acceptable.

### Escrow
**Not found** in any job or finance pages.

### Provider Cash Balance
**Not found** anywhere.

### Credit Wallet Health
**Not found** anywhere.

### Bargain (as user-visible label)
Occurrences found in `provider/pricing/page.tsx`:
- Data field `bargain_floor` → displayed as **"Min Floor Price"** label ✓
- Explanatory text in info panels: "bargain floor" used to explain the concept (not as a UI heading) — in context of "Administrators define base, minimum, maximum, and bargain floor."
- This is informational technical prose, not a primary UI label.

## Verdict: PASS
No forbidden labels found in job-related or finance pages. Privacy/compliance "Withdraw" usage is semantically correct. Pricing page uses "Min Floor Price" as the user-facing label.
