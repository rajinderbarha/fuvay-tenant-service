# Phase 4 — Remaining Blockers

None of these block certification (all hard gates pass; the ticket's own
waiver for environment-limited manual smoke applies). Carried forward,
honestly documented:

1. **No true interactive browser session available in this environment** —
   permanent constraint, confirmed via tool search. Evidence-based smoke
   substitute used per this ticket's own explicit authorization.

2. **`purchase_package()` write-path still references a phantom,
   unmigrated table** (`TenantPackagePurchase` / `tenant_package_purchases`
   — confirmed absent from the live database) and will 500 if actually
   called via `POST /v1/admin/tenants/{tenant_id}/packages/{package_id}/purchase`.
   The **read** path (`get_tenant_purchases`) was fixed this sprint to
   query the real `tenant_package_assignments` table instead — the write
   path was intentionally left alone because fixing it requires deciding
   how package purchase/selection should interact with
   `TenantPackageAssignment`'s approval lifecycle, which is Phase 5's
   "tenant approval runtime" territory per this ticket's own explicit
   exclusion.

3. **Two parallel security-deposit write surfaces exist**:
   `package_commerce`'s mark-paid/refund/forfeit (fixed this sprint — no
   longer shadowed, audit labels corrected) and a separate, more complete
   Finance Hub-style approve/reject/record-offline/refund/adjust workflow
   used by the actual `/admin/finance/deposits` frontend page. Both operate
   on the same `security_deposits` table. Not consolidated this sprint — a
   genuine architecture decision requiring product input on which workflow
   is canonical, not a "fix the bug" task.

4. **No dedicated `/admin/finance/settings` page** — the required settings
   are real and correct, but live under the generic `/admin/settings` page
   rather than a finance-specific one. Not a defect (the ticket's own Module
   11 says "or inside: /admin/platform-settings" as an acceptable
   alternative), documented for completeness.

5. **The systemic ₹-in-log-message Windows console-encoding crash pattern**
   (bug #4 in the bug-fix report) was fixed at its 2 confirmed occurrences
   in `platform_commerce/ledger.py`. Other engines' error messages were not
   audited for the same pattern (out of Phase 4's package/credit/deposit
   scope) — flagged as a platform-wide logging-configuration risk worth a
   dedicated future pass, not something to chase file-by-file under this
   ticket.

6. **No dedicated Finance Admin / Read-only Admin / Restricted Admin
   platform roles exist** to test permission behavior by that literal name
   (same finding as every prior permission-closure sprint this session) —
   the underlying `require_permission` mechanism was verified live and
   works correctly for any role lacking a given permission (tested with
   `tenant_owner`, which has zero `packages.*`/`finance.*` permissions).

None of the above represent a usage-credits-as-cash violation, a
deposit/credit mixing violation, a TypeScript failure, or a skipped manual
smoke — the four conditions this ticket names as automatic `NOT_READY`/`PARTIAL_READY`
triggers. All were checked explicitly and none apply.
