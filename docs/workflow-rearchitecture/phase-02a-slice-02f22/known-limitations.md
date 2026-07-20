# Known Limitations — Slice 2F-22

1. **Tenants cannot actually pay for a package.** By removing self-attested
   payment without a verifier to replace it, the tenant-facing purchase is
   now strictly an unpaid request pending admin approval. This is the correct
   fail-closed outcome — fabricating payment success was the defect — but it
   is a genuine product capability gap, not a complete purchase flow. See
   `product-decisions-required.md` #1.

2. **Duplicate-pending concurrency race.** SELECT-then-INSERT with no unique
   constraint; concurrent identical requests can create two `pending_review`
   rows. Cannot duplicate credits or money (activation is `LIMIT 1` and
   `verify_tenant` is one-shot), so impact is a stale orphan row. Correct fix
   requires a migration, prohibited this slice.

3. **Live concurrency and end-to-end HTTP behaviour are unverified.** No
   database or live server exists in this environment; every DB-backed test
   fails with `ConnectionRefusedError` / `httpx.ConnectError` (long-standing
   baseline). All 50 new tests are deterministic source/schema/signature
   assertions. The authorization behaviour of `require_tenant_owner_mutation`
   against real principals is inherited from its use in 2F-20, not re-proven
   over HTTP here. Stated as an environment exclusion rather than claimed.

4. **Read-only UI gating not audited.** The backend now denies purchase to a
   read-only tenant owner, which is the load-bearing control, but whether the
   tenant portal hides the purchase button for such users was not verified.

5. **Package eligibility controls absent.** No `is_purchasable`, tenant-private
   packages, vertical restriction, availability window, or internal-package
   flag exists. Reported rather than invented.

6. **No refund, reversal, renewal, upgrade or stacking semantics** exist in
   this model. Not invented.

7. **Razorpay dev-mode bypass.** `verify_payment_signature` returns `True`
   when the gateway is unconfigured. Pre-existing, out of scope, and it does
   not affect this route (which never marks paid under any configuration).

8. **Legacy dead path retained.** `purchase_package` /
   `TenantPackagePurchase` still exist against a table that was never
   migrated. Legacy tests in `test_sprint5_packages.py` exercise this dead
   method directly — they pass, but they do not test the live path. Removal
   was out of scope.

9. **Two stale Slice-2D canary tests remain failing** and were deliberately
   not rewritten, per this slice's explicit prohibition.

10. **`mutation-enforcement-matrix.csv` remains stale** as a legacy per-domain
    summary. Consistent with 2F-19/2F-20/2F-21 convention; the row-level
    inventory CSV is the authoritative denominator.
