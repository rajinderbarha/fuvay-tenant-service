# Canonical Booking Contract Verification — UX-06 Round 4

Real inspection of `app/engines/home_service_booking/service.py` +
`app/engines/final_records/creation_service.py` (Workstream 5):

- **Correct pipeline**: draft → serviceability → price-estimate →
  match-and-price → confirm-price-choice → `mark_ready_for_confirmation`
  (implicitly required, status must be `ready_for_confirmation`) →
  `POST /v1/customer/confirm/home-service-booking/{id}` → creates
  `ServiceBooking` + `ServiceJob` (per `confirm_router.py`'s own response
  fields `booking_id`/`job_id`). Confirms the ServiceBooking→ServiceJob
  pipeline, kept distinct from Booking→field_ops.Job throughout.
- **Customer identity is server-derived**: every draft/confirm endpoint takes
  `customer_id = uuid.UUID(user.user_id)` from `get_current_user`'s JWT
  context — never a client-supplied body field. Confirmed by reading every
  route in `customer_router.py`/`confirm_router.py`.
- **Tenant/provider selection follows canonical matching**: `match-and-price`
  calls `match_provider_and_price(...)` which the router's own docstring
  states runs "the full eligibility gate ... and selects exactly ONE
  provider — the customer never sees or picks from a list." Client cannot
  supply a `tenant_id`/`provider_id` anywhere in the draft/confirm request
  bodies (confirmed: `ConfirmRequest` is just `{customer_confirmation: bool}`).
- **Offering ID is canonical**: draft creation resolves `offering_slug` server-
  side against the real `MasterService` table (`start_booking_draft`); the
  client never supplies a raw offering UUID directly to the confirm step.
- **Address ownership**: `requires_address` per-offering (confirmed
  `ac_repair.requires_address: false` in the real catalog response — this
  offering does not require an address field at all, an honest finding this
  round; other offerings may require it and would need an owned-address check
  not yet exercised).
- **Serviceability/price are authoritative**: both computed server-side and
  stored on the draft row (`draft.serviceability_status`, `draft.price_snapshot`)
  — the confirm step reads these, never trusts client-echoed values.
- **Client cannot override final price**: confirmed — no price field exists
  anywhere in `ConfirmRequest`.
- **Duplicate submission / idempotency**: real `Idempotency-Key` header
  (confirmed Round 3), backed by `ConfirmationLockService` — verified this
  round that the header mechanism is genuinely present in the route signature,
  not merely documented.
- **Booking reference / detail retrieval**: `confirm_router.py`'s success
  response includes `booking_number`/`job_number` directly — this is what
  `DeepSeekChatScreen.tsx` displays and what would drive navigation to
  `BookingDetail`.

## What Round 4 could not yet prove live

`mark_ready_for_confirmation` (the gate before `confirm` will accept a draft)
requires a real `BargainRule` (platform-wide pricing/negotiation policy,
`master_service_id`-scoped, no such row exists for `ac_repair` in this dev DB)
plus a bookable `provider_visibility_statuses` row for the matched tenant —
neither was seeded this round (see test-data-environment-safety.md for why:
`BargainRule` is shared canonical config, out of the safe isolated-tenant seed
scope). This is the real, precise, newly-discovered reason booking submission
itself (Workstream 4's final steps) could not be completed live this round.
