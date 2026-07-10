# Phase 4 — Finance Bug Fix Report

## Bugs found and fixed

1. **`request_id` was a hardcoded placeholder, never a real ID, on every
   `package_commerce` response.** `_svc()` and `_ok()` both read
   `request.headers.get("X-Request-ID", "—")` — since no client ever sends
   that header, every single package/wallet/deposit/commission response
   (success *and* the service layer's own `request_id` field used in audit
   logs) carried the literal string `"—"` instead of the real
   `req_xxxxxxxxxxxx` ID that `RequestIDMiddleware` already generates for
   every request onto `request.state.request_id`. Fixed both call sites to
   read `request.state.request_id` first. Live-confirmed: `request_id`
   fields now show real IDs like `req_6abc5885d9c6`.

2. **Route collision silently shadowed the real security-deposit
   endpoints.** `tenant_engine/admin_router.py` defined
   `GET /{tenant_id}/security-deposit` and
   `POST /{tenant_id}/security-deposit/mark-paid` at the identical paths as
   `package_commerce/admin_router.py`'s versions. Because `tenant_engine`'s
   router is mounted *earlier* in `main.py`, its bare, un-audited,
   envelope-less, non-permission-gated duplicate always won — the real
   implementation I had just permission-wired was **unreachable dead code**.
   Removed the 2 duplicate routes from `tenant_engine`; the canonical,
   audited, `request_id`-carrying endpoint is now actually served.

3. **Copy-paste bug in deposit audit action labels.** `admin_refund_deposit`
   and `admin_forfeit_deposit` both logged `action="security_deposit_paid"`
   — the same label as the *mark-paid* action — instead of their own
   distinct names. Fixed to `"security_deposit_refunded"` /
   `"security_deposit_forfeited"` so the audit trail actually distinguishes
   which action occurred.

4. **A ₹ (Rupee sign, U+20B9) embedded directly in two `ServiceOSException`
   messages crashed Windows console logging** (`'charmap' codec can't
   encode character '₹'`), turning a clean, expected `402`
   insufficient-balance rejection into a raw, unhandled `500 Internal
   Server Error` — silently masking the exact validation behavior Phase
   4's acceptance criteria requires ("Debit that makes balance negative is
   rejected... UI shows request_id"). Found in `platform_commerce/ledger.py`
   in both `debit_wallet()` (usage credits) and the security-deposit draw
   function. Fixed both messages to describe amounts in plain numeric
   terms without an inline currency glyph — live-confirmed the same
   negative-balance debit now returns a clean `402` with a real
   `request_id` and no crash.

5. **Two endpoints the frontend already calls did not exist on the
   backend**, both 404/500ing silently: `GET /v1/admin/packages/purchases`
   (global tenant-package-assignment list) and
   `GET /v1/admin/packages/audit-logs` (global package/finance audit log).
   Also found the *existing* tenant-scoped purchases endpoint
   (`GET /v1/admin/tenants/{tenant_id}/packages/purchases`) queried a
   phantom, unmigrated table (`TenantPackagePurchase` / `tenant_package_purchases`
   — confirmed absent from the live database), so it 500'd on every call.
   Fixed by pointing the purchases read-path at the real, live
   `tenant_package_assignments` table instead, and added both missing
   endpoints (registered *before* the path-parameterized `/{package_id}`
   route to avoid a second, self-inflicted route-collision bug — caught and
   fixed during this same sprint after an initial misplacement). Live-confirmed
   all 3 paths now return `200` with real data instead of `404`/`500`.

6. **Frontend/backend field-name mismatch on the audit log response** —
   the frontend's `packageApi.auditLogs()` expected `{ logs, count }` but
   the new backend endpoint (matching this ticket's own required audit
   schema: `actor_user_id`, `action_type`, `target_type`, `target_id`,
   `old_value_json`, `new_value_json`, `request_id`) returns `{ items,
   total }` with those exact field names. Updated the frontend's
   `PackageAuditLog` TypeScript interface and the one consuming page
   (`app/admin/packages/page.tsx`'s Audit tab) to match, and added a
   Request ID column to that table — TypeScript re-confirmed clean (0
   errors) after the change.

7. **Missing data**: the baseline package had zero `PackageLimit` rows —
   the ticket's required `staff_limit=5` / `service_area_limit=5` did not
   exist. Created both via the real, audited `POST .../packages/{id}/limits`
   API (not direct DB insertion) — confirmed live afterward.

8. **Docstring said "escrow"** — `platform_commerce/models.py`'s
   `SecurityDeposit` class docstring read *"Per-tenant escrow."* Not a
   user-facing or API-exposed string (so it did not trip the hard forbidden-
   label gate), but incorrect terminology per this ticket's own business
   rules. Fixed to "Per-tenant security deposit."

## New schema addition (contained, additive)

Added a `request_id` column to `PackageAuditLog` (migration `112`) — the
model had no way to record which request produced an audit entry, so
`request_id` could never be surfaced on package/wallet/deposit audit rows
even after fixing bug #1 above. This closes the ticket's explicit
audit-record schema requirement ("Every mutation audit must include ...
request_id").

7. **Live crash reported by the user in production-shaped use**:
   `Tenant360Page` (`app/admin/tenants/[id]/page.tsx`) threw
   `TypeError: Cannot read properties of undefined (reading 'replace')` at
   `tx.type.replace(...)` in its wallet Transaction Ledger tab. Root cause:
   the page's `WalletTransaction` TypeScript type and rendering assumed
   fields `id`/`type`/`notes`/`job_id`, but the real backend endpoint it
   calls (`GET /v1/commerce/tenants/{id}/wallet/transactions`, a third,
   separate wallet-ledger surface in `platform_commerce`) actually returns
   `txn_id`/`txn_type`/`description`/`reference_id`+`reference_type` — a
   pre-existing field-name mismatch that had simply never been exercised
   before, because Demo AC Services had zero wallet transactions until this
   sprint's certification top-up/adjust test created its first two real
   rows. Fixed the `WalletTransaction` interface and the ledger-row
   rendering in `Tenant360Page` to match the real backend field names;
   confirmed live via direct API call that the shape now matches exactly,
   and via SSR fetch of `/admin/tenants/{id}` that the page renders `200`
   with no error markers. Added a regression test
   (`test_tenant360_wallet_transaction_fields_match_backend`).

## Bugs found, not fixed (documented as blockers, correctly out of scope)

- `purchase_package()` (the write-path for `admin_purchase_package`) still
  creates a `TenantPackagePurchase` row against the same phantom,
  unmigrated table — this will 500 if actually called. Not fixed because
  the real fix requires deciding how package *purchase/selection* should
  interact with `TenantPackageAssignment`'s lifecycle, which is Phase 5's
  "tenant approval runtime" territory per this ticket's own explicit
  exclusion ("Do not implement Tenant approval runtime... Actual package
  activation during tenant approval is Phase 5"). Documented, not patched
  over.
- The systemic Windows-console ₹-encoding crash (bug #4) likely affects
  other, unrelated engines too (grepped and found similar ₹-embedding
  patterns in `finance_hub/service.py` and `customer_credits/service.py`,
  though those specific occurrences are JSON payload *data* values, not
  exception messages piped through structlog, so they were not confirmed
  to crash and were left untouched — fixing every ₹ usage repo-wide is a
  platform-level logging/encoding configuration fix, out of this ticket's
  narrow finance-foundation scope).
