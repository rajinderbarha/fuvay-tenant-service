# Customer Capability Matrix — Phase D

This is the human-readable companion to `registry.ts`, the machine-readable
source of truth. Every classification below was produced this phase from
one of two evidence sources, never from prior documentation or the deleted
historical customer app:

1. **Live OpenAPI schema introspection** of the actual running FastAPI app
   (`app.openapi()["paths"]`, generated directly from real `@router`
   decorators). 210 `/customer`-scoped paths (and several role-neutral
   `/v1/me/*`, `/v1/customers/me/*` paths customers also use) were
   enumerated from a clean run of `app.main:app` this phase.
2. **Direct source reads** of the specific router/service/model files named
   in each row's notes.

Nothing below is `RUNTIME_PROVEN` — no live authenticated HTTP call was
made against a running server + database this phase. The strongest tier
reached is `SOURCE_VERIFIED`, and only where the underlying file was
actually opened and read, not just listed by the OpenAPI introspection.

**Total capabilities audited: 122. Evidence totals: SOURCE_VERIFIED 88 ·
PARTIAL 16 · MISSING 12 · ROLE_BLOCKED 4 · DISCONNECTED 1 · NOT_APPLICABLE 1
· RUNTIME_PROVEN 0 · VERTICAL_DISABLED 0.**

## Headline findings

- **The canonical Home Services pipeline is real and connected.**
  `/v1/customer/home-services/booking-drafts/*` → confirm → creates
  `ServiceBooking` + `ServiceJob` (`final_records` models) — confirmed by
  direct source read, not just route existence.
- **Customer booking cancel/reschedule is CONNECTED, not disconnected.**
  This reverses the phase's default assumption: `POST /v1/customer/
  bookings/{id}/cancel` and `/reschedule` both call
  `HomeServiceJobAssignmentService`, which operates on the canonical
  `ServiceBooking` — confirmed by direct source read
  (`home_service_assignment/customer_router.py`). The genuinely
  disconnected thing is a *separate* legacy `/v1/bookings/*` "Booking
  Engine" (`BookingService`) that this app must never call.
- **Customer quote approval is genuinely supported**, including a real
  `Idempotency-Key` mechanism on approve — the strongest idempotency
  evidence found anywhere in the customer API this phase.
- **There is no live bargaining/negotiation API for customers.** Pricing is
  system-computed (`price-estimate`, `confirm-price-choice`); "bargain"
  routes exist only as admin configuration (`/v1/admin/pricing/
  bargain-rules*`). All bargain-submission capabilities are `MISSING`.
- **Parts/change-order customer approval is a genuine backend gap.** The
  status vocabulary (`customer_approval_pending`, `customer_approved`,
  `customer_rejected`) is fully modeled in
  `app/engines/execution/constants.py`, but every parts-request route is
  provider/staff-scoped only. No customer route exists at all.
- **No customer-facing app-bootstrap endpoint exists** (no min-version,
  feature-flag, or maintenance-mode read for the customer role). Vertical
  visibility must be inferred from which categories the catalog endpoint
  actually returns.
- **Three pairs of parallel/duplicate surfaces** were found and are
  flagged, not silently resolved: two booking-confirmation routes
  (structured booking-drafts vs. AI-chat-drafted), two AI chat session
  surfaces (`ai-chat` vs `ai`), and two invoice surfaces (`invoices` vs
  `service-invoices`). Phase E must pick one canonical entry point per
  case — this phase deliberately does not guess.
- **No live location/GPS tracking exists.** `ServiceJob` has no
  coordinate columns; tracking is discrete status stages only
  (`on_the_way`, `reached_site`, ...). Do not build a moving map.
- **Direct-pay confirmed, no platform checkout.** `PAYMENT_MODE_HOME_
  SERVICES = "customer_pays_provider_directly"` in source. Usage-credit
  endpoints exist but are deliberately excluded from this registry's
  `exposableInUi` set.

## Matrix by group

| Group | Capabilities | SOURCE_VERIFIED | PARTIAL | MISSING | ROLE_BLOCKED | DISCONNECTED | N/A |
|---|---|---|---|---|---|---|---|
| Application bootstrap | 6 | 0 | 2 | 4 | 0 | 0 | 0 |
| Authentication and session | 10 | 10 | 0 | 0 | 0 | 0 | 0 |
| Customer profile | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| Addresses | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| Vertical and catalog discovery | 8 | 7 | 1 | 0 | 0 | 0 | 0 |
| Booking draft | 9 | 8 | 1 | 0 | 0 | 0 | 0 |
| Pricing and bargaining | 8 | 3 | 0 | 4 | 1 | 0 | 0 |
| Booking (incl. legacy warning) | 8 | 7 | 0 | 0 | 0 | 1 | 0 |
| Service job and tracking | 11 | 10 | 0 | 1 | 0 | 0 | 0 |
| Inspection and quote | 8 | 7 | 1 | 0 | 0 | 0 | 0 |
| Parts and change orders | 6 | 0 | 0 | 3 | 3 | 0 | 0 |
| Completion and payment information | 7 | 4 | 2 | 0 | 0 | 0 | 1 |
| Reviews | 5 | 4 | 1 | 0 | 0 | 0 | 0 |
| Communication | 8 | 6 | 2 | 0 | 0 | 0 | 0 |
| Notifications | 6 | 4 | 2 | 0 | 0 | 0 | 0 |
| Privacy and consent | 4 | 3 | 1 | 0 | 0 | 0 | 0 |

*(Column totals are per-capability, hand-tallied from `registry.ts`; the
authoritative machine count is the 122/88/16/12/4/1/1 total above, verified
by `src/domain/capabilities/__tests__/registry.test.ts`.)*

## Full detail

For the exact endpoint, data model, offline classification, blocker text
and verification source of every one of the 122 entries, read
`registry.ts` directly — it is the single source of truth and this
document intentionally does not duplicate every field to avoid the two
drifting apart. Query it at runtime via `getCapability(key)`,
`capabilitiesForVertical(vertical)`, or `capabilitiesByEvidence(evidence)`.

## Known backend blockers requiring future closure

1. **Parts/change-order customer surface does not exist.** Backend models
   the customer-approval state but exposes no route for it. (`parts.*`)
2. **No live bargaining API for customers.** Only admin bargain-rule
   configuration exists. (`pricing.bargainSubmitOffer` and siblings)
3. **No customer-facing app-bootstrap/feature-flag/min-version endpoint.**
   (`appConfig.*`)
4. **Duplicate booking-confirmation entry points** (structured
   booking-drafts vs. AI-chat draft) need a single canonical choice before
   Phase E builds a confirm button against either.
5. **Duplicate AI chat session surfaces** (`ai-chat` vs `ai`) need backend
   clarification on which is current.
6. **Duplicate invoice surfaces** (`invoices` vs `service-invoices`) need
   the same resolution.
7. **No live location/GPS tracking data** — any "provider is X minutes
   away" UI in a later phase must be built on ETA/status text, never a map.
