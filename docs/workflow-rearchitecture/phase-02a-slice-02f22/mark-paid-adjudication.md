# mark_paid Adjudication — Slice 2F-22

## Classification

**`CLIENT_SETTLEMENT_ATTESTATION_TRUSTED`**

Secondary: `CLIENT_PAYMENT_STATE_TRUSTED` (the same defect viewed as a state
transition rather than an assertion of fact).

**NOT `CLIENT_AMOUNT_TRUSTED`.** This corrects Slice 2F-21's label. No
monetary amount was ever accepted from the client on this route: every
financial value (`price_amount`, `security_deposit_amount`,
`included_spendable_credits`, `lead_credits`, `validity_days`,
`billing_cycle`) was already read from the authoritative `ServicePackage`
record. The defect was that the tenant could assert *that payment had
occurred*, not *how much it was*.

## Trace, end to end (pre-2F-22)

| Stage | Behavior |
|---|---|
| Schema type | none — body was untyped `payload: dict` |
| Default | absent → `bool(None)` → `False` |
| Read at | `tenant_router.py`, `bool(payload.get("mark_paid"))` |
| Passed as | `create_package_assignment(is_paid=...)` |
| Purchase status effect | `"paid_pending_approval"` instead of `"pending_review"` |
| Payment status effect | `paid_at = now()` — a timestamp asserting settlement |
| Payment reference | `payment_reference_id` = client string, unverified |
| Activation effect | none directly (`starts_at`/`expires_at` stay NULL) |
| Credit effect | none directly |
| Wallet / ledger effect | none directly |
| Entitlement effect | none directly |
| Audit effect | `tenant.package_selected` recorded `is_paid: true` |
| Notification effect | none |

## Why it mattered despite "no direct effect"

The absence of a *direct* credit effect made this look benign. It was not,
for two compounding reasons:

1. **Activation actively prefers self-attested rows.**
   `activate_tenant_package_assignment` selects its candidate with
   `ORDER BY paid_at DESC NULLS LAST`. A forged `paid_at` therefore sorts
   *ahead* of honest unpaid selections. Activation is what grants wallet
   credits, storage quota and commission rate.

2. **It corrupted the human decision.** The admin approving a tenant sees
   `paid_pending_approval` plus a plausible `payment_reference_id`. The
   defect's real payload was manufacturing evidence for the human who
   authorizes the money-moving step.

So the route did not issue credits itself — it forged the record that causes
someone else to issue them.

## Disposition applied

Per the mission's preferred order, the **first** option was taken: the field
was removed from the tenant-facing schema entirely.

- `TenantPackagePurchaseRequest` declares **no fields** and sets
  `extra="forbid"`, so `mark_paid` (and `payment_reference`, and any
  monetary/entitlement field) is **rejected with 422**, not silently ignored.
- The handler passes `is_paid=False` and `payment_reference=None` as
  literals — there is no code path from client input to paid state.
- A tenant purchase now creates only `pending_review`, the safe unpaid state
  the model already supported. No state was invented.

## Service-layer gate (defence in depth)

Router dependencies do not replace service-layer integrity, so
`create_package_assignment` now requires an explicit `payment_authority`
whenever `is_paid=True`:

| Authority | Caller | Basis |
|---|---|---|
| `gateway_signature_verified` | `public_registration` | `verify_payment_signature()` (HMAC-SHA256) already returned True |
| `admin_attestation` | `admin_router` | human admin under `P.PACKAGES_CREATE` |
| `tenant_unpaid_request` | `tenant_router` | **never permitted to be paid** |

Anything else — including the default `"unspecified"` — raises
`PAYMENT_AUTHORITY_REQUIRED` **before any database work**. This is a hard
failure, not a silent downgrade to unpaid: a caller that believes it recorded
a payment must not be left thinking it succeeded.

Additionally, an unpaid selection carrying a `payment_reference` raises
`PAYMENT_REFERENCE_WITHOUT_PAYMENT` — an unverifiable transaction reference
on an unpaid row is exactly the artifact that would mislead the approving
admin.

## Verification

`TestMarkPaidRemoved` (4 tests) and `TestServiceLayerPaymentAuthority`
(7 tests) in `tests/test_phase2f22_tenant_package_purchase_authorization.py`.
The fail-closed tests construct the service with `db=None`: the guard raises
before persistence is ever attempted, which would otherwise crash — so they
double as no-partial-persistence proof.
