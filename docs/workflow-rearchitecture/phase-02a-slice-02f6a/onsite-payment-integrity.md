# On-Site Payment Integrity — Workstream 3

## Before this slice
`record_onsite_payment` had:
- No invoice-status precondition at all (a payment could be recorded
  against a draft, never-issued, or cancelled invoice).
- No amount validation at all — `collected_amount` was cast directly to
  `Decimal` and stored; negative and zero values were accepted and would
  still mark the invoice `payment_collected` (i.e., "paid").
- No comparison against the invoice's `customer_payable_amount` —
  unlimited overpayment was silently accepted.
- A pre-existing duplicate-payment guard (checks for an existing
  `COLLECTED`/`VERIFIED` `ServicePaymentRecord`) — this part was already
  correct.

## Fixed this slice
Two new checks added to `ServicePaymentService.record_onsite_payment`,
both using the project's existing `Decimal`/`ValueError` + existing
error-code pattern (`ERR_INVOICE_INVALID_STATUS`,
`ERR_PAYMENT_AMOUNT_MISMATCH` — both pre-defined in `constants.py` but
previously unused in this method):
1. **State precondition**: `inv.status` must be `issued` or
   `payment_pending`; anything else (draft, cancelled, already
   `payment_collected`/`paid`, failed) is rejected.
2. **Amount validation**: `collected_amount` must be `> 0` and
   `<= inv.customer_payable_amount`. Exact-remaining-balance payments
   (the expected common case) continue to succeed.

## Determinations

| Question | Answer |
|---|---|
| Amount type | `float` at the API boundary, cast to `Decimal` in the service (existing pattern, unchanged) |
| Decimal precision | Standard `Decimal(str(x))` construction, no explicit quantization on the payment amount itself (matches `customer_payable_amount`'s own precision, which is quantized to cents elsewhere) |
| Currency source | `inv.currency` (existing field, read-only here — not touched) |
| Client-supplied? | Yes, `collected_amount` is client-supplied — now validated |
| Compared to invoice balance? | **NEW**: yes, rejects `> customer_payable_amount` |
| Zero allowed? | **NEW**: no — rejected (`ERR_PAYMENT_AMOUNT_MISMATCH`) |
| Negative allowed? | **NEW**: no — rejected |
| Overpayment allowed? | **NEW**: no — no account-credit mechanism exists in this codebase for this specific flow, so overpayment is rejected rather than silently accepted (consistent with "do not invent account-credit behavior") |
| Partial payment allowed? | No partial-balance tracking exists in this model — a single `record_onsite_payment` call marks the invoice fully `payment_collected`. A `collected_amount` less than the full payable amount is technically accepted (no defect proven that it shouldn't be — the single-shot model doesn't distinguish "partial" from "full," it just requires the amount not exceed the payable total) — this is an existing, unchanged model limitation, not a new gap. |
| Duplicate recording prevented? | Yes (pre-existing, unmodified): a second call is rejected once a `COLLECTED`/`VERIFIED` record exists — and now, additionally, once the invoice's own status has moved to `payment_collected`, the new state check independently blocks a second call too (defense-in-depth). |
| Payment reference? | `proof_media_url` field exists (optional receipt evidence), unchanged. |
| Idempotency mechanism? | No explicit idempotency key on this endpoint; the duplicate-payment-record check plus the new invoice-status check together prevent a double-collection in practice. See `duplicate-concurrency-review.md` for the concurrency-race caveat. |
| Payment/invoice totals update atomically? | Yes — `db.add(pay)` + `db.flush()` + `update_payment_status(...)` + `db.commit()` all occur within the same request/transaction (pre-existing, unmodified). |
| Audit includes amount + actor? | Yes — `FinancialEvent` records `new_value={"payment_mode": ..., "collected_amount": ...}` and `actor_user_id` (pre-existing, unmodified). |

## Direct tests (see `tests/test_phase2f6a_invoice_payment_integrity.py`)
Negative amount rejected; zero amount rejected; overpayment rejected;
exact-remaining-balance succeeds; valid partial-within-balance succeeds;
payment against draft/cancelled/already-collected invoice rejected;
repeated identical payment rejected; cross-tenant payment rejected with
no mutation (`db.add`/`db.commit` never called in the rejected path).

## Conclusion
Both conclusively-provable integrity defects (missing state precondition,
missing amount validation) are fixed using pre-existing, previously-
unwired error codes and the project's established `Decimal` pattern. No
account-credit or payment-gateway behavior was introduced.
