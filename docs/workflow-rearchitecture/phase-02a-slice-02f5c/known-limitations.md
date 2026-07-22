# Known Limitations — Slice 2F-5C

1. **Credit-wallet adapter idempotency-key contract gap.**
   `admin_topup_wallet`/`admin_adjust_wallet` generate a random key when
   the client omits one, defeating retry-safe dedup for that specific
   call shape. Disposition: `PRODUCT_DECISION_REQUIRED` (see
   `credit-wallet-adapter-integrity.md`). Not fixed — no natural stable
   business reference exists for a manual adjustment, and mandating a
   client-supplied key would be a breaking contract change.

2. **Audit-event gaps**: the 6 package feature/limit CRUD routes and
   `admin_calculate_commission` do not raise an audit event, unlike every
   other mutation in the file. Not fixed — the correct event-name/payload
   convention is a design choice, not a mechanical fix, per
   `audit-notification-verification.md`.

3. **Cross-pipeline commission risk.** `package_commerce`'s own
   `calculate_commission`/`deduct_commission` are internally consistent,
   but a documented risk exists in `platform_commerce.service`'s own
   `deduct_commission` (a different module, out of scope) around how it
   interprets an existing `CommissionRecord` row. See
   `alternate-commerce-route-audit.md`. Not fixed — the affected code
   lives outside `package_commerce.admin_router`.

4. **`admin_calculate_commission`'s trusted `job_value`.** The commission
   base value is client-supplied (admin-trusted) rather than independently
   re-derived from an invoice/job record within this module. Not fixed —
   this endpoint is already maximally-trusted (`require_super_admin`),
   and inventing a cross-record validation would require deciding which
   record is authoritative (out of scope, a product/architecture
   decision).

5. **UI-level role-based button gating not independently verified**
   component-by-component. Backend 403 enforcement was fully verified for
   all 20 mutations across all 12 personas; frontend redesign was
   explicitly out of scope.

6. **No independent concurrency/locking load test.** Row-locking presence
   (credit-wallet adapter) and absence (package assignment, commission
   calculation) were confirmed by source inspection, not exercised under
   real concurrent load. Consistent with the platform-wide pattern
   documented in Slice 2F-5B.

7. **6 orphaned service methods** (`admin_mark_deposit_paid`,
   `admin_refund_deposit`, `admin_forfeit_deposit`, `admin_topup_wallet`,
   `admin_adjust_wallet` on `PackageCommerceService`, plus the standalone
   `purchase_package`) remain in `service.py` as dead code, not deleted
   this slice (deletion of unreferenced code was not in the mission's
   permitted-fix list; a regression test locks in that they stay
   unreachable).

8. **Product-policy questions left open by design**: whether `admin_finance`
   should ever be granted `PACKAGES_*` permissions remains unresolved
   (see `product-decisions-required.md`) — a deliberate, policy-driven
   non-closure, not an oversight.
