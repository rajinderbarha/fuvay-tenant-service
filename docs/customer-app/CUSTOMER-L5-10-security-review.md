# CUSTOMER-L5-10 — Security Review

## Ownership Enforcement

`confirm_price_choice`'s draft lookup (`self._require_draft(draft_id,
customer_id)`, `service.py:684`) enforces draft ownership before any
tier resolution runs — unchanged pattern from every prior sprint. This
client sends only the path's `draftId` and a literal tier string — no
provider ID, no session ID, no amount — leaving no client-constructible
input that could probe another customer's or tenant's pricing/bargain
data.

## No Internal Fee/Floor Data Ever Reaches the Client's Rendered UI

`bookingSummarySchema` accepts `allowed_offer_min`/`allowed_offer_max`/
`platform_fee_amount` (they arrive in the same flat `booking_summary`
object as the customer-visible fields) but this sprint's UI code never
reads or renders any of the three — verified by grep (no hits outside the
schema definition and test fixtures under `features/bargain/`). No
internal score, margin, commission, or `BargainRule` configuration field
is ever returned by `confirm-price-choice` at all — structurally
impossible to leak.

## No Client-Submitted Price Values

This sprint's only outbound field beyond the path's `draftId` is
`price_tier`, always one of three UI-controlled literal strings
(`TIER_ORDER`) — never a raw amount, never a route-param-injected value.
The resulting `customer_offer` is always read back from the backend's own
response, never computed or asserted client-side.

## No Sensitive Logging

`bargain_offer_submit_started`/`_succeeded`/`_failed`/`_error` log calls
pass only the tier name (a non-sensitive, closed 3-value enum) — never the
actual amount, never the platform fee, never the provider name. Verified
by direct review of every `logger.*` call site added this sprint.

## No Production Mocks

Grepped `features/bargain/` for `mock`, `fake`, `TODO`, `FIXME` — none
found. Every rendered amount traces to a real, schema-validated backend
response (either `match-and-price`'s `price_options`, reused from
CUSTOMER-L5-09, or `confirm-price-choice`'s `booking_summary`).

## Cross-Tenant/Cross-Customer Isolation

Relies entirely on the backend's own draft-ownership check (above). This
sprint adds no new client-side authorization logic, and no new local
persistence surface (`cache-policy.md`) requiring its own clearing logic
beyond the existing unconditional `queryClient.clear()` on
logout/account-switch.

## No Fake Counteroffer / No Fake Bargain Session

Per `counteroffer-contract.md`'s exhaustive finding, this sprint builds no
counteroffer UI, no bargain-session concept, no attempt counter, and no
rate-limit/cooldown handling — all would require either fabricating
non-existent backend behavior or building dead client code against the
explicitly product-deactivated `MANUAL_BARGAIN_RULES_ENABLED` module. This
is itself a security-adjacent finding: building a plausible-looking
negotiation UI with no real backend enforcement behind it would be a
customer-trust risk (implying a negotiation happened when it structurally
could not have), which this sprint deliberately avoids.

## Rate Limiting — Real, Disclosed Absence

Per `attempt-and-rate-limit-policy.md`, no rate limiting or attempt
capping applies to `confirm-price-choice`/`match-and-price` anywhere in
this backend. This is a genuine backend-side gap this sprint cannot close
from the frontend — documented prominently in `known-gaps.md` rather than
masked with a fake client-side limiter that would give a false sense of
protection.

## Currency Trust

`currency` is rendered exactly as the backend returns it via the
already-audited `formatCurrency` utility, reused unchanged from
CUSTOMER-L5-09 — this sprint adds no new currency parsing or formatting
logic of its own.
