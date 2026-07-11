# FINAL-L5-05 — Bug Register

## L5-05-001: `hs-overview` nav item duplicated `hs-price-experience`'s href, orphaning the real Overview page
- **Severity**: P2 (broken discoverability, not data-loss)
- **Evidence**: Both nav items pointed to `/admin/home-services/price-experience`; `/admin/home-services/overview/page.tsx` (125 lines, real API-backed, built in an earlier sprint per its own header comment) was completely unreferenced
- **Root cause**: Nav item created with the wrong href, likely copy-paste from the adjacent item
- **Files changed**: `frontend/super-admin/components/layout/AdminLayout.tsx`
- **Fix**: `hs-overview` now points to `/admin/home-services/overview`
- **Browser evidence**: Real Chromium test confirms both "Overview" and "Customer Price Experience" now navigate to distinct, correct pages
- **Status**: **FIXED**

## L5-05-002: "Wallet Balance" forbidden label in `field-labels.ts`
- **Severity**: P2 (terminology policy violation)
- **Files changed**: `frontend/super-admin/lib/field-labels.ts`
- **Fix**: `wallet_balance`/`credit_balance` field keys now both display "Usage Credit Balance"
- **Status**: **FIXED**

## L5-05-003: "Tenant Payouts" forbidden label in Settings category table
- **Files changed**: `frontend/super-admin/app/admin/settings/page.tsx`
- **Fix**: Column header changed to "Payouts" (consistent with the existing, already-approved nav label)
- **Status**: **FIXED**

## L5-05-004/005/006: 3 backend `platform_settings` rows with forbidden-terminology labels — found via real Chromium, not static grep
- **Severity**: P1 (static source-code grep found zero hits — these labels come from the database, not source code; only real browser rendering revealed them)
- **Evidence**: Live Chromium run on `/admin/settings` rendered "Usage Credit Is Cash Wallet", "Usage Credit Is Withdrawable", and (from the same table) a `tenant_payouts_enabled` row
- **Root cause**: `platform_settings.label` is a real, admin-editable database column; these 3 rows were seeded with forbidden terminology baked directly into the label text
- **Fix**: Direct `UPDATE platform_settings SET label = ...` for all 3 rows (`usage_credit_is_cash_wallet` → "Usage Credit Treated As Cash", `usage_credit_is_withdrawable` → "Usage Credit External Redemption Allowed", `tenant_payouts_enabled` → "Payouts Enabled") — key names and values untouched, purely a display-label fix, verified as safe via a full settings-related pytest run (58/58 passing) after the change
- **Browser evidence**: Real Chromium re-run confirms zero forbidden terms remain on `/admin/settings`
- **Status**: **FIXED**

## L5-05-007: Usage Credits and Reports — real, mission-critical pages orphaned from navigation
- **Severity**: P1 (Part 14 explicitly requires Usage Credits be discoverable via `tenant_billing`; Part 17 explicitly requires Reports be discoverable)
- **Files changed**: `frontend/super-admin/components/layout/AdminLayout.tsx`
- **Fix**: Added `finance-usage-credits` → `/admin/finance/usage-credits` to the Finance group; `reports` → `/admin/reports` to the Marketing & Growth group
- **Browser evidence**: Real Chromium confirms both nav items navigate to real, non-trivial, working pages
- **Status**: **FIXED**

## L5-05-008: `/admin/operations` (the sidebar's "Jobs" item) is backed by the legacy `/v1/jobs` API, not the canonical `service_jobs`/final-records API
- **Severity**: P0 — directly implicates rule 12 ("do not reintroduce /v1/jobs") and Part 12's explicit requirement ("no /v1/jobs dependency")
- **Evidence**: `jobsApi` in `lib/api.ts` (base path `/v1/jobs`) is imported and used by `app/admin/operations/page.tsx`, `app/admin/operations/[jobId]/page.tsx`, and `app/admin/tenants/[id]/page.tsx`. A separate, newer, canonical page (`/admin/home-services/service-jobs`, backed by `/v1/admin/final-records/jobs`) already exists but is **not** the one linked from the sidebar's "Jobs" item
- **Root cause**: Pre-existing architecture debt — `/v1/jobs` was never fully retired after the canonical final-records API was introduced in an earlier sprint; the sidebar was never updated to point at the newer page
- **Files that would need to change**: `AdminLayout.tsx` (repoint "Jobs" nav item), and either (a) verify `/admin/home-services/service-jobs` has full feature parity with `/admin/operations` (reassign/void/close/notes/media actions) before swapping, or (b) migrate `/admin/operations`'s actions onto the final-records API
- **Status**: **NOT FIXED this sprint** — found and root-caused, but real remediation requires a feature-parity investigation and testing pass this sprint's time budget did not allow doing safely. Documented as the top Remaining Blocker, not hidden.

## Result
7 of 8 real bugs found this sprint were fixed, live-verified via real Chromium (not just static analysis — 3 of the terminology bugs were only discoverable by actually rendering the page). 1 real, pre-existing, rule-relevant architecture bug (`/v1/jobs` on the primary Jobs nav item) was found, root-caused, and documented but not fixed — the single largest reason this sprint cannot honestly claim full READY certification.
