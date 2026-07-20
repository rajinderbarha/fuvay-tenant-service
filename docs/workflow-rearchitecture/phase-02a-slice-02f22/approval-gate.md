# Slice 2F-22 Approval Gate

## Final status

**SECURITY_DOMAIN_INTEGRITY_AND_PRIVACY_CLOSED_PRODUCT_POLICY_BLOCKED**

## SECURITY — CLOSED

| Requirement | Status | Evidence |
|---|---|---|
| Canonical tenant-owner persona | MET | `require_tenant_owner_mutation`; staff/technician/customer/guest denied |
| Mutation-capable scope | MET | read-only `access_scope` now denied (was not) |
| Server-derived tenant | MET | JWT only; cross-tenant purchase unrepresentable |
| Package eligibility | MET | active + not soft-deleted |
| **No client payment-state authority** | **MET** | `mark_paid` removed from schema; `is_paid=False` literal; service-layer `payment_authority` gate |
| No client amount/currency authority | MET | never existed; now explicitly rejected |
| No cross-tenant purchase | MET | no tenant field accepted |
| No weaker same-record route | MET | both alternate creators hold real authority (gateway signature / admin permission) |
| Runtime verification exits zero | MET | `runtime-verification-report.md` |

The mission's bar — *"Do not claim security closure while a tenant can
self-attest payment"* — is satisfied: there is no code path from client input
to paid state, enforced at both the schema and the service layer.

## DOMAIN INTEGRITY — CLOSED

| Requirement | Status | Evidence |
|---|---|---|
| Purchase state machine explicit | MET | `package-purchase-state-machine.csv` |
| Paid/active requires authoritative evidence | MET | `payment_authority` allow-list, fails closed pre-persistence |
| Price snapshot server-derived | MET | all fields from `ServicePackage` |
| Credits/entitlements issue exactly once | MET | `idempotency_key` per assignment + one-shot `verify_tenant` |
| Duplicate/concurrent cannot duplicate benefits | MET | activation `LIMIT 1`; approval one-shot per tenant |
| Invalid actions create no partial state | MET | `no-partial-persistence-proof.md` (guards fire with `db=None`) |
| Transaction behaviour coherent | MET | service flushes, handler commits |

The mission's bar — *"Do not claim domain-integrity closure while unpaid
purchases can issue credits, entitlements or package activation"* — is
satisfied: a tenant purchase activates nothing and issues nothing.

**Disclosed residual:** the duplicate guard is SELECT-then-INSERT, so
concurrent identical requests can create two `pending_review` rows. This
cannot duplicate benefits (traced end to end in
`duplicate-idempotency-policy.md`); the impact is a stale orphan row. The
correct fix is a partial unique index — a migration, prohibited this slice.
Closure is claimed on the benefit-duplication criterion, which is what the
mission specifies, with the race disclosed rather than concealed.

## PRIVACY — CLOSED

All 8 related reads derive their tenant from the JWT; no read accepts a
tenant, purchase or assignment identifier, so there is no IDOR surface. No
payment reference, gateway metadata or internal note is exposed — and a
tenant-created assignment no longer carries a `payment_reference_id` at all.
All 8 handlers confirmed non-mutating (checked explicitly because 2F-20 found
a state-mutating GET elsewhere). See `package-purchase-read-privacy.md`.

## GLOBAL COVERAGE — CLOSED

**206/226 → 207/226.** 19 unprotected across 8 modules. Live recount:
`total: 226 protected: 207`.

Every numeric recount assertion repo-wide was located by grep and updated
(4 test files, 7 assertion sites) — the step 2F-20 skipped, which is what
caused its regression. Assertions reading 2F-21's *own* historical slice CSVs
were deliberately left at 20, since rewriting them would falsify that slice's
truthful point-in-time finding.

## PRODUCT POLICY — BLOCKED (expected and permitted)

- No payment gateway wired to `ServicePackage` purchases, so paid
  self-service does not exist (the honest consequence of removing fabricated
  payment).
- Duplicate-pending unique index requires a migration.
- Package eligibility controls (`is_purchasable`, tenant-private, vertical
  restriction, availability window) do not exist and were not invented.
- Renewal, stacking, upgrade, refund policies undefined.
- Granular package-purchase permission for `staff` not created.

See `product-decisions-required.md`.

## Regression — proven, not inferred

Zero newly-failing node IDs; exactly one resolved. 11108 passed / 86 failed /
111 errors / 14 skipped. The +51 passed reconciles exactly as 50 new tests
plus 1 resolved. Established by exact before/after failing-node-ID
comparison, per this slice's mandated methodology.

## Preserved (re-confirmed)

field_ops 28/28 and 6/6; Booking, quote-checklist and invoice-lineage
closures; platform-notifications/chat-media closure; **compliance provider
closure (2F-20) intact and its export workflow NOT reopened**; Package
Commerce admin-router and Finance Hub closures; `PartsRequest` ServiceJob-only;
`Booking`/`ServiceBooking` and `field_ops.Job`/`ServiceJob` separate;
canonical roles only; `readonly@demo-ac-services.local` untouched; Migration
144 unapplied; Slice-2D canaries not rewritten.

## Scope discipline

No role, alias or permission added. No migration added or applied. No
pipeline merged. No payment gateway, callback infrastructure, checkout
frontend or subscription billing built. No new Package model. No pricing,
discount, renewal or stacking policy invented. No frontend or mobile file
modified. Four application files changed, all within the proven
payment-attestation bypass: `package_commerce/tenant_router.py`,
`package_commerce/service.py`, `package_commerce/admin_router.py`, and
`public_registration/router.py` (the latter two only to declare the authority
they already held).

## Stop condition

This response stops at the Slice 2F-22 approval gate. No other module has
been begun. 8 modules / 19 routes remain — `remaining-module-queue-update.csv`.

## Forward annotation (added by Slice 2F-23)
Slice 2F-23 reconciled the 19-route / 8-module queue this slice left behind
and selected the next module. **This slice's closure is CONFIRMED to stand**,
by test rather than assertion: `test_package_commerce_closure_still_intact`
asserts that `tenant_purchase_package` still resolves
`require_tenant_owner_mutation` and still passes `is_paid=False`, so the
reconciliation cannot silently coexist with a regression here.

The indirect-change audit found **zero coupling**: none of the ten source
files backing the 19 remaining routes references `package_commerce`,
`public_registration`, `payment_authority`, or `require_tenant_owner_mutation`
(`../phase-02a-slice-02f23/package-commerce-indirect-change-audit.md`). No
remaining route depends on the client-controlled payment-state behaviour this
slice invalidated.

Coverage is **UNCHANGED at 207/226**, 19 unprotected across 8 modules — the
figure this slice established, re-counted live.

2F-23 selected `app.engines.customer_reviews.provider_router` (2 mutations)
for Slice 2F-24, having found a **confirmed cross-tenant mutation**:
`flag_review` performs no ownership check and writes `review.status` on any
review in any tenant, behind a bare `get_current_user`. That module had been
carried forward in this slice's queue as MEDIUM severity, characterised only
by an impersonation risk — the second consecutive slice in which an inherited
queue severity proved understated on direct source reading.

This slice's regression methodology was applied and extended: failing node
IDs compared exactly (zero new, zero resolved), plus a `-rE` error-ID capture
that closes the error-comparison gap noted in
`../phase-02a-slice-02f23/regression-report.md` for future slices.

Final status for 2F-23: `NEXT_MODULE_SELECTED_COVERAGE_UNCHANGED`.
See `../phase-02a-slice-02f23/approval-gate.md`.
