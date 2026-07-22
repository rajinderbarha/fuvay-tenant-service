# Known Limitations

- **`InventoryService.receive_stock`'s `item_id`/`location_id` are not
  cross-checked against the trusted tenant** — only the request's
  `tenant_id` is validated; a caller could still reference an `item_id`/
  `location_id` belonging to a different tenant if guessed. This is a
  pre-existing object-ownership gap on `item_id`/`location_id` (distinct
  from the `tenant_id`-trust defect this slice fixed) and was out of this
  slice's specific held-route scope (which concerned the missing
  tenant_id trust, not a full item/location ownership audit).
- **`ds` module's 2 read-only routes (`churn/score`, `demand/forecast`)
  remain cross-tenant-readable** — any authenticated principal can pass
  any `tenant_id` to read another tenant's churn score or demand
  forecast. This is a privacy/information-disclosure gap on read paths,
  correctly out of scope for a mutation-enforcement objective
  (`READ_ONLY_EXCLUDE` disposition per the held-route taxonomy), but
  worth flagging for a future read-path hardening slice.
- **Booking's `customer_id` (when supplied by a non-customer caller) is
  not ownership-checked against the tenant** — pre-existing behavior,
  confirmed unrelated to this slice's `POST /v1/bookings` adjudication
  (which concerned tenant_id trust, already correct).
- Migration 144 remains unapplied, per mission OUT-OF-SCOPE list.
- N01 domain-integrity backlog unchanged, per mission OUT-OF-SCOPE list.
- `readonly@demo-ac-services.local` remains untouched, per mission
  PRESERVE list.
