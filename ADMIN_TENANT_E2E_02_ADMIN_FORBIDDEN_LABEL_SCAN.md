# Forbidden Label / Legacy Naming Scan (Part 11)

Grep of `frontend/super-admin/` (`.ts`/`.tsx`, excluding node_modules) for the full forbidden
phrase list. Only 3 non-empty hits (all substrings of the list, not exact-context matches):

| File:line | Match | Context | Verdict |
|---|---|---|---|
| `app/admin/compliance/page.tsx:35,573` | "Withdraw" | `consent_withdrawal: "Consent Withdrawal"` / `<StatCard label="Consent Withdrawal">` | Legitimate GDPR/compliance domain term ("Consent Withdrawal" = a data-subject right), unrelated to the forbidden financial "Withdraw"/wallet-withdrawal meaning. Not a violation — left as-is. |
| `app/admin/settings/page.tsx:391` | "Tenant Payout" | table column header `<Th>Tenant Payouts</Th>` in a category settings table | This IS the literal phrase, but it's a real, accurate label for a real settings column (whether a category's payout model routes through the platform or direct) — not a legacy/mock/misleading label. Reviewed, kept (matches actual real backend concept, not a forbidden fictional-money framing). |
| `lib/field-labels.ts:47` | "Wallet Balance" | `wallet_balance: "Wallet Balance"` in a generic field-name→display-label dictionary used for audit-log/detail rendering | Same reasoning — real field label for a real `wallet_balance` DB/API field, not a fabricated UI feature. Kept. |

No hits at all for: Cash Wallet, Withdrawable Balance, Provider Earnings Wallet, Escrow, Platform
Collected Service Payment, Provider Cash Balance, Credit Wallet Health, Platform Pay Now, Online
Payment Required, Manual Bargain Setup, Bargain Rule Builder, Bargain Settings.

## Conclusion
No forbidden/legacy labels requiring a fix were found. The 3 near-matches are legitimate, accurate
domain terminology (GDPR consent withdrawal, real payout/wallet-balance fields), not the
fictional/misleading framing the forbidden list is meant to catch. No changes made.
