# ADMIN-TENANT-E2E-05 — Forbidden Label Scan

Forbidden terms (per sprint policy — Home Services must never look like a cash/payout/withdraw/escrow/bargain product):
`Cash Wallet, Withdraw, Withdrawable Balance, Tenant Payout, Provider Earnings Wallet, Escrow, Platform Collected Service Payment, Provider Cash Balance, Credit Wallet Health, Platform Pay Now, Online Payment Required, Manual Bargain Setup, Bargain Rule Builder, Bargain Settings`

## Scan scope
`grep -rniE "<forbidden pattern>"` over `app/admin/finance`, `app/admin/tenants`, `app/admin/home-services` (all `.tsx` under these trees).

## Result: 2 hits, both compliant (explicitly negating the forbidden framing, not using it)
```
app/admin/tenants/[id]/page.tsx:2430: "...used for platform charges. They are not cash, not withdrawable, and not a payout balance."
app/admin/tenants/[id]/page.tsx:2831: "...not cash, not withdrawable. This will increase the provider's credit balance..."
```
Both are disclaimer/help copy on the "Usage Credit Ledger" tab and the "Add Usage Credits" modal, explicitly telling the admin the credits are **not** cash/withdrawable — the opposite of a violation; this is the correct, intended framing per the "Home Services = usage credits, not cash" architecture. No occurrence of any forbidden term is used as a label, button, or heading anywhere in the scanned trees.

## `/admin/finance/wallets` naming scrutiny (explicitly called out in the task brief)
The route path itself (`finance/wallets`) and its nav label ("Finance Hub" section groups it under Finance in the sidebar) do **not** use any of the literally-forbidden strings above. It is a real, separate `tenant_wallets`-backed system (see API Contract report) with its own generic "wallet balance" framing — legitimate wallet terminology used elsewhere in the codebase for provider-side commission/job-closing gating, not a violation of the specific forbidden-term list. Flagged as worth a naming/architecture review (two systems both plausibly called "wallet"/"credits" is confusing) but not a forbidden-label violation as literally defined.

## Verdict: PASS — no forbidden-label violations found; the two disclaimer occurrences are exactly the required negation, not a leak.
