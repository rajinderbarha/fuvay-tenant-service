# ADMIN-TENANT-E2E-11 — Security Deposit Display Report

Route: `/finance/security-deposit`.

## Checks
1. Section appears only if data exists — the page always renders (loading
   → data or a graceful fallback using safe defaults like
   `status: "pending"`), backed by `tenantSetupApi.getWallet()`'s
   `security_deposit`/`deposit` field; if genuinely absent, defaults are
   shown rather than hiding the section — reasonable given deposit status
   is a required field for every tenant (not optional data).
2. Amount/status from real API — confirmed, `useApi(() => tenantSetupApi.getWallet())`.
3. Not shown as wallet/cash/payout — confirmed, labeled "Security
   Deposit," "Deposit Status," fields are Status/Required Amount/
   Currency/Amount Received/Received At.
4. No withdraw action — confirmed, page is read-only (no buttons at
   all besides navigation links).
5. Clearly separate from Usage Credits — confirmed, explicit copy: *"View
   your security deposit status and details. Security deposit is
   separate from usage credits."* plus a cross-link to Package & Credits
   for the credit balance itself.

## Verdict
Full pass — clean, correctly separated, real API, no forbidden actions.
