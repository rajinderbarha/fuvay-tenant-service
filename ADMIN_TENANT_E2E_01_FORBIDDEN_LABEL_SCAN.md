# ADMIN_TENANT_E2E_01 — Forbidden Label Scan

Scanned `frontend/super-admin/app` and `frontend/tenant-portal/app` (`.tsx`, excluding `node_modules`)
for all 15 forbidden labels: Cash Wallet, Wallet Balance, Withdraw, Withdrawable Balance, Tenant Payout,
Provider Earnings Wallet, Escrow, Platform Collected Service Payment, Provider Cash Balance, Credit
Wallet Health, Platform Pay Now, Online Payment Required, Manual Bargain Setup, Bargain Rule Builder,
Bargain Settings.

## Findings
- No literal matches for: Cash Wallet, Withdrawable Balance, Tenant Payout (as an exact phrase; see note
  below), Provider Earnings Wallet, Escrow, Platform Collected Service Payment, Provider Cash Balance,
  Credit Wallet Health, Platform Pay Now, Online Payment Required, Manual Bargain Setup, Bargain Rule
  Builder, Bargain Settings — **zero matches, clean**.
- `admin/settings/page.tsx:391` — table header "Tenant Payouts" (plural, close to forbidden "Tenant
  Payout"). This is a real admin settings-config table header. **Flagged as a near-miss** — worth
  renaming to an allowed term (e.g. "Provider Price Range"/"Payment Collection Model") in a later sprint,
  but not fixed here since it's a table header describing a real per-category "Payment Collection" /
  finance-model config, not a customer-facing wallet feature. Documented, not blocking.
- All other "Withdraw"-containing hits (`account/privacy/page.tsx` in tenant-portal) are **GDPR consent
  withdrawal** ("Withdraw Consent", "Consent Withdrawal") — unrelated to money, false positives, no
  action needed.
- `admin/tenants/[id]/page.tsx` explicitly uses the ALLOWED framing: "Usage credits are internal
  ServiceOS credits ... They are not cash, not withdrawable, and not a payout balance." — this is
  correct, intentional anti-forbidden-label language, not a violation.

## Known pre-existing legacy page (flagged in a prior sprint, not fixed here)
`frontend/tenant-portal/app/(tenant)/wallet/page.tsx` — a legacy `/wallet` route still exists in the
tenant-portal nav tree (not present in the current `nav-config.ts` groups, meaning it's an orphaned
route reachable by direct URL only). Its component title ("WalletPage") itself doesn't render forbidden
strings directly on the surface examined, but the route naming ("wallet") itself is the legacy-naming
issue flagged in a prior sprint. **Status: still present, still not fixed** — trivial rename was not
attempted this sprint since the spec explicitly said not to feel obligated to fix it here.

`frontend/super-admin/app/admin/provider-wallets/page.tsx` — similarly named "Provider Wallets" admin
page, backed by `adminWalletApi`. Uses "Wallet" label directly in UI ("Provider Wallets", credit/debit
actions). Not one of the 15 explicitly forbidden strings, but adjacent to the "wallet" naming theme.
Documented for future cleanup, not modified this sprint (out of scope; would require confirming the
underlying data model is genuinely Usage-Credits-based before any rename).

## Result
CLEAN on the 15 forbidden strings verbatim. One near-miss ("Tenant Payouts" plural) and two known
legacy "wallet"-named pages documented for a future cleanup sprint.
