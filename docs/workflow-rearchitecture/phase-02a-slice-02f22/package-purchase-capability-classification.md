# Capability Classification — Slice 2F-22

## Pre-2F-22: `MIXED_UNSAFE_CAPABILITY`

The route was labelled simply "Purchase a package", but it combined two
capabilities with very different trust requirements:

1. `PACKAGE_PURCHASE_REQUEST` — record a tenant's selection (safe).
2. `MANUAL_PAYMENT_ATTESTATION` — declare that payment had been received,
   with a supporting transaction reference (**not safe from a tenant**).

The mission's instruction not to retain a vague "purchase" label applies
exactly here: the route marked payment complete and wrote a `paid_at`
timestamp, which is a settlement act, not a purchase request.

It did NOT activate a package, issue credits, change quotas, grant modules,
extend expiry, or write a financial ledger entry — all of those sit behind
admin activation. Verified by direct source read, not assumed.

## Post-2F-22: `PACKAGE_PURCHASE_REQUEST`

A single coherent capability: create an unpaid selection pending admin
approval. The `MANUAL_PAYMENT_ATTESTATION` capability was removed from the
tenant surface entirely; it survives only where an authority exists to
support it (gateway signature, or admin attestation).

Deliberately **not** classified as:

- `PACKAGE_PURCHASE_AND_PENDING_PAYMENT` — there is no payment to be pending;
  no initiate/confirm pair exists for this model.
- `FREE_PACKAGE_ACTIVATION` — the route never activates, regardless of price.
- `CREDIT_TOP_UP`, `PACKAGE_RENEWAL`, `PACKAGE_UPGRADE`,
  `PACKAGE_REPLACEMENT`, `ENTITLEMENT_ACTIVATION` — none of these semantics
  exist anywhere in the code path.
