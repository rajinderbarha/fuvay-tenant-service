# CUSTOMER-L5-11 — Review Contract

## Endpoint

`POST /v1/customer/home-services/booking-drafts/{draftId}/summary` →
`build_booking_summary` — real, re-confirmed this sprint (already
documented by CUSTOMER-L5-10 for this sprint's benefit).

## Field Classification

| Field | Classification | Editable this sprint? |
|---|---|---|
| `offering_name`/`offering_slug` | `CUSTOMER_VISIBLE`, `READ_ONLY` | No real edit-service route reachable with only a `draftId` — displayed read-only (see bargain-architecture.md's established pattern of not building a broken navigation target) |
| `issue_summary` | `CUSTOMER_VISIBLE`, `READ_ONLY` | Same reasoning |
| `address` (address_snapshot) | `CUSTOMER_VISIBLE`, `EDITABLE` | Yes — routes to `AddressSelection` |
| `city`/`zipcode` | `CUSTOMER_VISIBLE`, `READ_ONLY` | Fallback display only when `address` itself is absent |
| `preferred_date`/`preferred_time_window` | `CUSTOMER_VISIBLE`, `READ_ONLY` | No dedicated schedule-edit screen exists in this app yet (unchanged since CUSTOMER-L5-07's own "no `preferred_date` picker" gap) |
| `selected_provider` (5 real fields, already server-side stripped) | `CUSTOMER_VISIBLE`, `EDITABLE` | Yes — routes to `ProviderPreview` |
| `serviceability.serviceable`/`.status` | `CUSTOMER_VISIBLE`, drives `not_ready` messaging | Routes to `AddressSelection` when false |
| `ready_for_confirmation` | `CUSTOMER_VISIBLE`, the one field this sprint's UI branches its entire top-level state on | N/A — backend-computed, never inferred client-side |
| `selected_price_tier`/`customer_offer` | `CUSTOMER_VISIBLE`, `EDITABLE` | Yes — routes to `Bargain` |
| `payment_mode` | `CUSTOMER_VISIBLE`, `READ_ONLY` | Rendered as the payment-policy note |
| `allowed_offer_min/max`/`platform_fee_amount` | `INTERNAL_ONLY` | Present in the real, cumulative `booking_summary` blob (written earlier by `confirm-price-choice`) but never parsed by this sprint's `bookingSummarySchema` at all — structurally excluded |

## Not-Ready Handling

Per §24's requirement to "identify the section needing correction," this
sprint derives which section is incomplete **directly from real
sub-fields already present in the same response** — no separate
diagnostic call is made:

- `serviceability.serviceable === false` → "not serviceable" row → edit → `AddressSelection`
- `!selected_provider` → "no provider matched" row → edit → `ProviderPreview`
- `!selected_price_tier` → "no price chosen" row → edit → `Bargain`

This is a real, honest inference from the same real response fields
`mark_ready_for_confirmation` itself checks server-side (contract-matrix.md) —
not a fabricated diagnostic, since every one of these three real backend
sub-checks is independently visible in the same `booking_summary` object.

## Cancellation Policy — Disclosed Absence of a Real Backend Field

No structured cancellation-policy field exists anywhere in this flow's
real responses (verified this sprint — no `cancellation_policy`/
`free_cancellation_window`/similar field on `booking_summary`, the draft,
or `MasterService`). Per §19's explicit instruction not to hardcode policy
language if the backend or remote configuration provides it: neither does.
This sprint's cancellation-policy text
(`bookingReview.cancellationPolicyText`) is therefore static, deliberately
generic, non-committal app copy ("Cancellation terms will be confirmed by
the provider. Contact support if you need to cancel.") rather than an
invented specific policy (e.g., a fabricated "free cancellation up to 2
hours before" claim this backend cannot back up) — documented as a real
product gap in known-gaps.md, not silently papered over with invented
specifics.

## Consent — Disclosed Absence of a Real Backend Field

No consent/terms-acceptance field exists anywhere in this flow (verified
this sprint — `mark_ready_for_confirmation`'s real required-field check
never includes anything consent-shaped). This sprint renders no consent
checkbox: a checkbox with nothing server-side to persist its state against
would be UI theater, not a real acknowledgement mechanism. See
known-gaps.md.

## Test Coverage

`review-schema.test.ts` (4 tests): a real, fully-ready summary; a real
not-ready summary with only the one guaranteed field present; a missing
`ready_for_confirmation` fails closed; a fully malformed payload fails
closed.
