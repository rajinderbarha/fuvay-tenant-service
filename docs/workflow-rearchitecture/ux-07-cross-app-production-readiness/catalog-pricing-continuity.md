# Catalog/Pricing Continuity (Workstream 4)

Partially touched as a byproduct of the live E2E proof (Workstream 19), not
independently completed. Real finding carried over from that work:

- `ac_repair`'s real `ServicePricingRule` rows are scoped per
  `service_type_id` ("Split AC" / "Window AC"), with no unscoped fallback
  row. A booking draft whose `offering_type_id` is left null (which the
  draft's own `required_fields` response does not flag as required) will
  fail `match-and-price` with `PRICE_OPTIONS_UNAVAILABLE` even though
  pricing genuinely exists for the offering once a real service type is
  selected. This is a real, minor, previously-undocumented contract gap
  between the draft API's declared required fields and its actual
  functional requirements. See `api-contract-audit.csv` for the endpoint
  row and `live-e2e-evidence.md` step 5 for the full narrative.

Full continuity verification (catalog changes in super-admin propagating to
tenant-portal pricing, tenant-portal pricing propagating to customer-app
price display, etc.) not attempted this round — deferred.
