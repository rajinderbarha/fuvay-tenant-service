# Pricing Management Specification

Dimensions: service, job type, brand, option, zone, city-tier
(`PricingFixture`). Platform min/max always visible alongside tenant price;
below-minimum values are visually flagged (danger color + inline note) —
see `/dev/ux-03/pricing`. Effective-price preview shows the resolved price
after any zone override. Platform-controlled bounds are read-only; only
`tenantPrice` is editable (edit action gated `API_CONTRACT_REQUIRED` per
readiness-state-registry.csv).
