# Documentation Corrections — Slice 2F-22

## 1. Gap terminology corrected (mandated by this slice's brief)

Slice 2F-21 classified the `mark_paid` defect as **`CLIENT_AMOUNT_TRUSTED`**.
That label is **wrong** and is corrected here to
**`CLIENT_SETTLEMENT_ATTESTATION_TRUSTED`** (secondary:
`CLIENT_PAYMENT_STATE_TRUSTED`).

Basis, established by reading the service method rather than the route
signature: no monetary amount was ever accepted from the client. Every
financial value — `price_amount`, `security_deposit_amount`,
`included_spendable_credits`, `lead_credits`, `validity_days`,
`billing_cycle` — was already read from the authoritative `ServicePackage`
record. The tenant could assert *that payment had occurred*, never *how much*.

`CLIENT_AMOUNT_TRUSTED` applies only where an actual client monetary field is
trusted without authoritative recomputation. That condition was never met on
this route.

Corrected in: `mark-paid-adjudication.md`,
`package-purchase-capability-classification.md`,
`server-price-authority.md`, and the 2F-21 forward annotation.

## 2. Related-read count corrected

2F-21's `selected-next-module.md` listed **4** related reads. The router
declares **8** GET routes. The four omitted are the financially sensitive
ones: `/v1/tenant/credit-wallet`, `/v1/tenant/credit-ledger`,
`/v1/tenant/commissions`, `/v1/tenant/storage-quota`.

All 8 were audited this slice and found correctly tenant-scoped
(`package-purchase-read-privacy.md`). The omission did not affect 2F-21's
selection decision, but it understated the module's privacy surface.

## 3. Defect severity was understated, not overstated

2F-21 recorded the route as `PERMISSION_ONLY_NOT_SCOPE_AWARE` with a
client-field concern. Investigation found the compounding factor 2F-21 did
not identify: `activate_tenant_package_assignment` orders activation
candidates by `paid_at DESC NULLS LAST`, so a self-attested "paid" row was
actively **preferred** for activation — and activation is what grants wallet
credits, storage quota and commission rate. Recorded in
`mark-paid-adjudication.md`.

## 4. Payment verification — scope of the finding narrowed

Care was taken **not** to report a blanket
`PAYMENT_VERIFICATION_NOT_IMPLEMENTED`. Real HMAC-SHA256 verification exists
(`app/integrations/razorpay_client.py`) and is correctly used by
`public_registration` and `platform_commerce`. The accurate finding is that
no verifier is wired to the `ServicePackage` flow specifically. A blanket
claim would have been false and would have justified building payment
infrastructure this slice forbids. See `payment-verification-boundary.md`.

## 5. Forward annotation added to Slice 2F-21

Per the established pattern, `phase-02a-slice-02f21/approval-gate.md` carries
a new forward-annotation section recording that 2F-21's selection was
implemented, its `CLIENT_AMOUNT_TRUSTED` label corrected, and coverage
advanced 206 → 207.

## 6. Slice-2D canaries NOT touched

The two stale `test_phase2d_tenant_access_model.py` canaries remain failing
and were **not** rewritten, per this slice's explicit prohibition. They are
unrelated to package commerce and still require the
`tenant-readonly-decision.md` product conclusion to be revisited.
