# CUSTOMER-L5-15 — Recovery Contract

Per §36–41's recovery scenarios (expired SLA, provider rejection,
provider unavailability, assignment failure, price revision, stale
booking state):

## What real recovery capability exists today

- **Stale booking state**: already handled by the app-wide,
  cross-sprint pattern of `staleTime: 0` + refetch-on-mount (every query
  hook since CUSTOMER-L5-06) and the "backend wins" reconciliation
  established since CUSTOMER-L5-11's idempotency contract. No new work
  needed — this sprint's own screens (none added) would have inherited it
  automatically had there been a real mutation to build.
- **Provider rejection**: `home_service_assignment`'s real job-status
  vocabulary already includes a rejection path (surfaced via the shared
  `booking-status-registry.ts`, e.g. `customer_not_available` and the
  execution engine's own transitions) — the *customer-visible signal*
  that a provider rejected already flows through the existing
  `BookingDetailScreen`/`ServiceTrackingScreen` (CUSTOMER-L5-12/13). What
  does **not** exist is any customer-facing *action* to take in
  response (rematch, reschedule, cancel) — confirmed none of the three
  exist as real customer endpoints.
- **Expired SLA, provider unavailability, assignment failure, price
  revision**: no dedicated recovery-action endpoint exists for any of
  these. The customer's only real recourse today, per the existing,
  correct `BookingDetailScreen` copy, is contacting support out-of-band
  — which is honestly represented, not synthesized by this client.

## Why no "recovery options" screen is built this sprint

Every recovery scenario in the spec ultimately resolves to one of
"cancel" or "reschedule" as the corrective action — both of which this
sprint conclusively found have no real customer-facing implementation
for the canonical booking. A "Recovery Options" screen offering choices
that all lead to non-existent endpoints would be exactly the kind of
fabricated, convincing-looking-but-non-functional feature every previous
sprint's own standard explicitly prohibits. This client does not build
one.

## What this sprint does provide

Full source-level documentation (this file plus
`baseline-verification.md`/`contract-matrix.md`) of exactly which
recovery actions exist, which don't, and why — so a future sprint adding
real backend recovery endpoints has an accurate, pre-verified map of the
current job/booking status vocabulary to build against, rather than
starting from the spec's aspirational model.
