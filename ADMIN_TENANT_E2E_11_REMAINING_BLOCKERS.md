# ADMIN-TENANT-E2E-11 — Remaining Blockers

## Real bugs found and fixed this pass
1. **`/finance` rendered a legacy Wallet/Payouts page** violating this
   ticket's own business rules — "Wallet" tab, "Request Payout" with
   bank-account fields, "Payouts" history, Razorpay wallet top-up. Fixed:
   now redirects to the real, correct `/finance/package` (same pattern
   `/wallet` already used to redirect to `/finance`).
2. **`/finance/package`'s Usage Credit Balance card showed a stale `0`**
   — it read the old Sprint 23 `/v1/provider/wallet` endpoint, the exact
   same stale-wallet-concept bug HS9B already found and fixed once on
   the ledger page, but this sibling page was never updated. Fixed:
   rewired to the real `usageCreditsApi.getBalance()`, now correctly
   shows `3937`, matching the ledger page exactly. Added a real
   low-credit warning banner as part of the same fix (previously
   missing entirely on this page).
3. **Tenant notification bell had no `onClick`** — dead button, same
   pattern as the admin-side bug fixed in E2E-06B. Fixed: navigates to
   `/notifications`.
4. **Test-infrastructure gap**: the shared Playwright login helper only
   suppresses the *admin* app's onboarding tour overlay; the tenant
   app's tour uses a different `localStorage` key and was blocking
   clicks in every tenant-app test written against real Chrome. Fixed
   for this spec and documented for future tenant-app E2E work.
5. **A pre-existing static-inspection backend test** asserted a label
   against the now-redirected `/finance/page.tsx`; corrected to check
   the real page containing those labels.

## Real blocker found, not fixed — the sprint's actual verdict driver
**No tenant read-only/manager role tier exists in the backend at all.**
Live-verified: `tenant.readonly@serviceos.in` and
`tenant.manager@serviceos.in` both have `role: "tenant_owner"` in the
database — identical to the real owner account. A real, valid
`PUT /v1/settings/tenants/{tid}/{key}` mutation, sent with the read-only
seed account's real token, **succeeds (200)**. This was already
flagged as a known gap in E2E-10 ("frontend role guards may be
incomplete") but is now confirmed, via live verification, to be worse
than a frontend guard gap — there is no backend permission tier to guard
against for these seed accounts at all.

Not fixed this pass: building a real role tier (new role values, a full
audit of every tenant-mutation endpoint to gate on it, matching frontend
guards) is a significant, cross-cutting RBAC design effort — beyond this
ticket's "small backend fix" scope, and touches shared seed data that
other already-certified sprints may depend on. A real, strict, permanent
Playwright regression test now exists to guard this until it's properly
fixed (see Test Results report) — it currently fails as expected,
documenting the gap rather than hiding it.

## Everything else in scope: clean
Usage Credit Balance (real, correct, matching across pages), Usage
Credit Ledger (real, correct arithmetic, no duplicates), Completed Job
Deduction (real, correctly linked), Security Deposit (real, clean, no
withdraw action), Tenant Notifications (real, honest empty state,
correctly tenant-scoped), Settings (real, substantial, 5-tab surface,
no fake data), zero forbidden labels (after the `/finance` fix), zero
mock data, no direct-fetch bypasses, TypeScript clean, backend
regression clean (92/92).

## Final certification decision

`NOT_READY_TENANT_RBAC_FAILED`

Per this ticket's own explicit rule: *"If unauthorized mutation succeeds,
return NOT_READY_TENANT_RBAC_FAILED."* A real, live, valid mutation by a
nominally read-only tenant account succeeded — verified twice (once via
direct curl, once via a corrected, strict, automated Playwright
assertion that now permanently guards this gap). Every other area this
ticket covers is genuinely clean, and two real, previously-unknown
finance-data bugs were found and fixed along the way (the legacy wallet
page and the stale balance card) — but this one confirmed security gap,
per the ticket's own literal rule, is the correct, honest final verdict
rather than a `PARTIAL_READY` softening.
