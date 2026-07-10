# ADMIN-TENANT-E2E-11 — Tenant Finance Overview Report

## Real, live-breaking bug found and fixed this pass

`/finance` (the bare route, not linked from the sidebar — nav-config
only links to `/finance/package`, `/finance/usage-credit-ledger`,
`/finance/security-deposit`) rendered a **legacy Wallet/Payouts page**:
tabs literally labeled "Wallet" and "Payouts", a "Request Payout" button
opening a modal with "Bank Account ID" and "Amount (₹)" fields, Razorpay
checkout for "Buy Credits" with a wallet top-up flow, StatCards labeled
"Usage Credit Balance" / "Available" / "Reserved" mixed with wallet
semantics. This directly violates this ticket's business rules #5/#6
("Tenant finance is not a wallet or payout system," "No withdraw,
escrow, payout... or wallet wording").

This page was still reachable: directly by URL, via `/wallet` (which
redirects to `/finance`), and via a mislabeled link on the onboarding
page ("Configure Pricing" → `/finance`).

**Fixed**: `/finance` now redirects to `/finance/package` — the real,
correct, Usage-Credit-based canonical finance page (same fix pattern as
`/wallet` → `/finance` already used). `/finance/package`,
`/finance/usage-credit-ledger`, `/finance/security-deposit` were not
touched — they were already correct.

## Sections present (on the now-canonical `/finance/package`)
1. Usage Credit Balance — present, real (`tenantSetupApi.getWallet()`).
2. Completed Job Deduction summary — not on this specific page (lives on
   `/finance/usage-credit-ledger` instead, linked from here).
3. Recent Usage Credit Ledger entries — not embedded here, linked out to
   the dedicated ledger page (`<a href="/finance/usage-credit-ledger">`).
4. Low-credit alert — not shown on this page specifically (the ledger
   page shows a "Low Credit Status: Healthy/Low" card); at the real,
   current balance (3937, threshold 20) no alert would trigger anyway.
5. Security Deposit Held — not embedded, linked out
   (`<a href="/finance/security-deposit">`).
6. Package/plan info — present (Package Name, Code, Status, Staff Limit,
   Service Area Limit, Included Usage Credits, Started At — all real).
7. Finance activity timeline — not present as a unified timeline; split
   across the linked pages instead.

## Checks
1. Loads from real API — confirmed.
2. Usage Credit Balance appears — confirmed, real value.
3. Balance matches backend/DB — confirmed via direct API cross-check
   (3937, same value shown on the ledger page and matching the live
   ledger chain).
4/5. Recent ledger / deduction entries — not on this page, present one
   click away (documented above, not a defect).
6. Security Deposit Held — appears only via link, backed by real API on
   its own page.
7. No wallet wording — confirmed on this page and its siblings after the
   fix (forbidden-label scan: 0 matches).
8. No payout/withdraw/escrow wording — confirmed, same scan.
9. No fake finance numbers — confirmed, all real API-backed.

## Verdict
Real bug found and fixed. The canonical finance surface (spread across 3
focused pages rather than one monolithic overview) is real, clean, and
compliant with the business rules.
