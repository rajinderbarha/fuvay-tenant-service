# CUSTOMER-L5-10 — Negotiated Price Contract

## Backend Field

There is no separate "negotiated price" record/table/ID. The negotiated
price **is** `draft.booking_summary.customer_offer` (a float), alongside
`selected_price_tier` (`"low"|"mid"|"high"`) for context — both written
atomically by `confirm-price-choice` (contract-matrix.md).

## Field-by-Field Classification

| Backend field | Customer-visible label (this sprint) | Ownership | Validity | Draft mapping | Privacy classification |
|---|---|---|---|---|---|
| `customer_offer` | The large "confirmed price" amount on the `confirmed` state | Backend-resolved, never client-submitted | No expiry — see below | `draft.booking_summary.customer_offer` | `CUSTOMER_VISIBLE` |
| `selected_price_tier` | Not shown as raw text (the amount itself is shown instead) | Backend-recorded, reflects the customer's real tap | Same as above | `draft.booking_summary.selected_price_tier` | `CUSTOMER_VISIBLE` (used internally for the `TIER_ORDER` UI logic, not rendered as the literal word) |
| `selected_provider_name` | Shown under the confirmed amount | Backend-resolved (from the already-matched provider) | Same | `draft.booking_summary.selected_provider_name` | `CUSTOMER_VISIBLE` |
| `selected_tenant_id` | Not displayed | Backend-resolved | Same | `draft.booking_summary.selected_tenant_id` | Stored only in the parsed schema; never rendered as UI text (mirrors L5-08/L5-09's treatment of `tenant_id`) |
| `selected_zipcode` | Not displayed this sprint | Backend-resolved | Same | `draft.booking_summary.selected_zipcode` | `CUSTOMER_VISIBLE` in principle, simply not rendered — no product requirement to repeat the zipcode on this screen |
| `allowed_offer_min` / `allowed_offer_max` | Never shown | Backend-internal-adjacent | Same | `draft.booking_summary.allowed_offer_min/max` | `INTERNAL_ONLY` this sprint (bargain-floor/ceiling-adjacent, same reasoning as CUSTOMER-L5-09's identical fields) |
| `platform_fee_amount` | Never shown | Backend-internal | Same | `draft.booking_summary.platform_fee_amount` | `INTERNAL_ONLY` |
| `payment_mode` | Shown as a one-line note | Backend-fixed value | Same | `draft.booking_summary.payment_mode` | `CUSTOMER_VISIBLE` |

## Validity

No expiry field exists for the negotiated price specifically (unchanged
from CUSTOMER-L5-09's identical finding for the estimate itself) — only
the generic, whole-draft `expires_at` (24 hours from draft creation). This
sprint does not display a "valid until" countdown for the negotiated price
for the same reason L5-09 didn't for the estimate: there is no real value
to show.

## Draft Mapping

`draft.booking_summary` is a merged (not replaced) JSON blob — confirmed
by direct source reading (`service.py:704-716`, `{**(draft.booking_summary
or {}), ...}`). This sprint's client never reads or writes this field on
the shared draft cache (unlike `selected_tenant_id`/`status`, which
L5-08/L5-09 do patch) — `booking_summary` was never part of the
`bookingDraftSchema` any screen parses, and no other screen currently
depends on it, so there is nothing to keep in sync client-side.

## Review Boundary

The real precondition for the next stage
(`build_booking_summary`'s `ready_for_confirmation` flag, CUSTOMER-L5-11
scope) is `selected_price_tier` being set — which this sprint's flow
always achieves before its own "Continue" button becomes reachable
(the `confirmed` state is the only state with a "Continue" action).

## Test Coverage

Covered by `bargain-schema.test.ts`'s request/response shape tests and
`bargain-state.test.ts`'s `confirmed`-state derivation tests — both use
fixtures shaped exactly like the real `booking_summary` dict this sprint's
own source reading confirmed field-by-field.
