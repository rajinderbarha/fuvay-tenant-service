# Customer capability matrix

`registry.ts` is the machine-readable source of truth for customer-app
capabilities. UI may expose a capability only when its evidence classification
and role permit it; missing, disconnected, and role-blocked entries stay hidden.

## Current product decisions

- Home Services uses the canonical booking-draft pipeline and creates a
  `ServiceBooking` plus `ServiceJob` at confirmation.
- The selected provider's published fixed price is authoritative. Inspection
  services disclose the visit fee and require quote approval before work.
- Customer cancellation and rescheduling call the canonical job-assignment
  service, including eligibility, reason, and concurrency checks.
- Customer app bootstrap is served from `/v1/public/app-config/customer`, with
  minimum-version, store links, maintenance state, and enabled verticals.
- Home Services payment is made directly to the provider. Platform usage
  credits are a provider entitlement/penalty mechanism, not customer money.
- Live GPS tracking is not advertised; tracking shows evidence-backed job
  stages and ETA text only.
- Customer-facing provider selection is disabled. The matching engine chooses
  one eligible, bookable provider for the exact service and PIN code.

## Known restricted capability

Parts/change-order actions are provider/staff controlled. Customer approval is
not shown unless a customer-authorized endpoint is available and verified.

For endpoint, evidence, role, blocker, and visibility details, inspect
`CUSTOMER_CAPABILITY_REGISTRY` in `registry.ts` and its registry tests.
