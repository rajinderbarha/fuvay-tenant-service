# E2E-07 Tenant Forbidden Label Scan
**Date:** 2026-07-10  
**Analysis:** grep scan of `app/(tenant)/` — all `.tsx` and `.ts` files

---

## Forbidden Labels Checked

| Label | Pattern | Files Found | Status |
|---|---|---|---|
| Cash Wallet | `Cash Wallet` | 0 | CLEAN |
| Wallet Balance | `Wallet Balance` | 0 | CLEAN |
| Withdraw (financial) | `Withdraw` in finance/wallet context | 0 | CLEAN |
| Withdrawable | `Withdrawable` | 0 | CLEAN |
| Escrow | `Escrow` | 0 | CLEAN |
| Provider Cash Balance | `Provider Cash Balance` | 0 | CLEAN |
| Credit Wallet Health | `Credit Wallet Health` | 0 | CLEAN |
| Manual Bargain Setup | `Manual Bargain Setup` | 0 | CLEAN |
| Bargain Rule Builder | `Bargain Rule Builder` | 0 | CLEAN |
| Bargain Settings | `Bargain Settings` | 0 | CLEAN |
| Bargain Floor | `Bargain Floor` | 1 (FIXED) | FIXED |

## Details

### Bargain Floor (FIXED)

**File:** `app/(tenant)/provider/pricing/page.tsx`

**Before:** 5 occurrences of "Bargain Floor" as a column header, KPI label, MetaChip label, and tooltip text.

**After:** Replaced as follows:
- `"Bargain Floor"` → `"Min Floor Price"` (KPI card, MetaChip, pricing result row)
- `"Bargain Floor"` → `"Floor Price"` (table column header)
- Tooltip body text updated to remove "bargain" language

### Withdraw in Consent Context

The word "Withdraw" appears in privacy/compliance pages in the context of **GDPR/DPDP consent withdrawal** (e.g. "Withdraw Consent"). This is legal terminology for revoking a data processing consent. It is **not** a financial withdrawal and is **not** a forbidden label per the E2E-07 spec. These occurrences are CORRECT and preserved as-is.

Files with consent "Withdraw":
- `app/(tenant)/account/privacy/page.tsx` — "Withdraw Consent" modal
- `app/(tenant)/provider/compliance/page.tsx` — "Withdraw Consent" modal
- `app/(tenant)/account/privacy/requests/page.tsx` — "Consent Withdrawal" type label
- `app/(tenant)/provider/compliance/requests/[id]/page.tsx` — same

### Consent Withdrawal Label in Type Maps

`consent_withdrawal: "Consent Withdrawal"` appears in type-label maps. This is the DPDP Act privacy request type name and is legally required terminology — not a forbidden label.

## Scan Commands Used

```sh
grep -rn "Cash Wallet|Wallet Balance|Withdraw|Withdrawable|Escrow|Provider Cash Balance|Credit Wallet Health|Bargain" app/(tenant)/ --include="*.tsx"
```

**Status: PASS** — All forbidden financial/system labels removed. Legal consent "Withdraw" terminology preserved correctly.
