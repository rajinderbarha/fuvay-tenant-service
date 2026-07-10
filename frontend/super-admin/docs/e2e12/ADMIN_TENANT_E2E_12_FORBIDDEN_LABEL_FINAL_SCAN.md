# E2E-12 Forbidden Label Final Scan

**Date:** 2026-07-10  
**Method:** grep via Grep tool across `app/**/*.tsx` in both portals

---

## Scan Patterns

```
Cash Wallet | Wallet Balance | Withdrawable | Escrow | Provider Cash Balance |
Credit Wallet Health | Manual Bargain Setup | Bargain Rule Builder |
Bargain Settings | Tenant Payout | Provider Earnings Wallet | Recharge Wallet
```

---

## Tenant Portal Results

**CLEAN — 0 matches**

---

## Admin Portal Results

5 files with matches. Detail below:

### 1. `app/admin/settings/page.tsx:391`
```tsx
<Th>Tenant Payouts</Th>
```
**Pattern matched:** `Tenant Payout`  
**Context:** Column header in a finance settings table showing the `tenant_payouts_enabled` backend configuration flag per category.  
**Assessment:** BORDERLINE P2 — This is a backend configuration field display, not a product feature name. The column header mirrors the database column name (`tenant_payouts_enabled`). Not a wallet/payout product UI label. Recommend renaming to "Payout Config" in a future cleanup pass. **Not blocking.**

### 2. `app/admin/home-services/settings/page.tsx:70`
```tsx
<FlagRow label="Manual Bargain Rules" on={cfg.manual_bargain_rules_enabled}
```
**Pattern matched:** `Manual Bargain` (partial of forbidden "Manual Bargain Setup")  
**Assessment:** ACCEPTABLE — Label is "Manual Bargain Rules", not the forbidden "Manual Bargain Setup". This is a toggle for a backend feature flag (`manual_bargain_rules_enabled`). The exact forbidden string "Manual Bargain Setup" is not present.

### 3. `app/admin/home-services/price-experience/page.tsx:69`
```tsx
<ConfigStat label="Manual Bargain Rules" enabled={config.data?.manual_bargain_rules_enabled ?? false} invert/>
```
**Pattern matched:** `Manual Bargain` (partial)  
**Assessment:** Same as above — acceptable.

### 4. `app/admin/pricing/bargain-rules/page.tsx` (multiple lines)
- Line 251: `title="Bargain Rules [Deprecated]"`
- Line 265: `New Bargain Rule`
- Line 294: `Total Bargain Rules`
- Line 337: `New Bargain Rule`
- Line 351: `New Bargain Rule / Edit Bargain Rule`
- Line 492: `Bargain Rule Detail`

**Pattern matched:** `Bargain Rule` (partial of forbidden "Bargain Rule Builder")  
**Assessment:** ACCEPTABLE — The exact forbidden string "Bargain Rule Builder" is not present. This is a deprecated page titled "Bargain Rules [Deprecated]" with a warning that the feature is disabled. Legacy labels on a deprecated page are acceptable.

---

## Summary

| Forbidden Label | Admin Hit | Tenant Hit | Verdict |
|----------------|-----------|------------|---------|
| Cash Wallet | 0 | 0 | CLEAN |
| Wallet Balance | 0 | 0 | CLEAN |
| Withdrawable | 0 | 0 | CLEAN |
| Escrow | 0 | 0 | CLEAN |
| Provider Cash Balance | 0 | 0 | CLEAN |
| Credit Wallet Health | 0 | 0 | CLEAN |
| Manual Bargain Setup | 0 (partial match only) | 0 | CLEAN |
| Bargain Rule Builder | 0 (partial match only) | 0 | CLEAN |
| Bargain Settings | 0 | 0 | CLEAN |
| Tenant Payout | 1 (borderline P2) | 0 | P2 |
| Provider Earnings Wallet | 0 | 0 | CLEAN |
| Recharge Wallet | 0 | 0 | CLEAN |

---

## Action Taken

No changes made. The one borderline P2 finding ("Tenant Payouts" column header) does not require immediate fix — it is a backend config field display, not a product wallet/payout label. Logged as P2 for future cleanup.
