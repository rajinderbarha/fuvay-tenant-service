# Invoice Item Integrity — Workstream 4

## Before this slice
`add_item` had no validation on `quantity` or `unit_price` at all.
`line_total = qty * unit_price` was computed and stored unchecked, then
summed into whichever `item_type` bucket the caller supplied inside
`_recalculate`. A negative `quantity` or `unit_price` would silently
produce a negative `line_total`, which — if the caller labeled the item
`item_type="part"` (or any non-"discount" type) — would reduce that
bucket's subtotal exactly as if it were an undeclared, unbounded
discount, with no distinct discount mechanism, no bound, and no separate
audit trail identifying it as a discount.

## Discount mechanism determination
`item_type == "discount"` exists only as a **summing category** inside
`_recalculate` (`elif item.item_type == "discount": discount += t`) —
it is not a validated, bounded discount system. There is:
- No distinct discount flag or type-specific validation.
- No bound preventing a discount from exceeding the subtotal (driving
  the total negative).
- No separate audit event for discounts vs. ordinary items.
- No mechanism preventing an ordinary item from being submitted with
  `item_type` other than `"discount"` while still carrying a negative
  `line_total`.

**Conclusion: negative invoice items are an integrity gap, not an
intentional discount mechanism.** Per the mission's explicit instruction
("If no explicit discount mechanism exists, reject negative values"),
negative values are rejected outright — no discount system was invented.

## Fixed this slice
Added to `ServiceInvoiceService.add_item` (using the pre-existing,
previously-unused `ERR_INVOICE_ITEM_INVALID` error code):
- `quantity <= 0` → rejected (a zero-quantity line item has no meaning;
  a negative quantity is the primary vector for the undeclared-discount
  gap).
- `unit_price < 0` → rejected. **Zero** `unit_price` remains allowed — a
  legitimate free/no-charge line item (e.g., a warranty part) has no
  distinct-discount-mechanism ambiguity, since it does not reduce any
  other item's value, it simply contributes `0` to its own bucket.

A double-negative (`quantity=-1, unit_price=-10`, which would otherwise
net to a *positive* `line_total=+10`) is still rejected, since the
`quantity <= 0` check fires independently of the sign of the resulting
product — confirmed via a dedicated test.

## Other determinations

| Question | Answer |
|---|---|
| Line-total calculation | `quantity * unit_price` (existing, unmodified formula) |
| Tax calculation | Handled via a separate `item_type == "tax"` bucket in `_recalculate`, summed as-is — no per-item validation added or needed (tax items are conceptually always positive in this model; no evidence of negative-tax abuse found) |
| Client-supplied total? | No — the invoice's `total_amount`/`customer_payable_amount` are always server-recalculated via `_refresh_totals`, never accepted from the client (pre-existing, unmodified) |
| Server recalculates invoice total? | Yes — every `add_item` call triggers `_refresh_totals`, which re-sums all items plus the per-category platform fee (pre-existing, unmodified) |
| Items after issue? | Rejected (`status != INV_DRAFT` guard, pre-existing, unmodified) |
| Items after payment? | Rejected (payment moves status past `draft`, so the same guard applies) |
| Items after cancellation/void? | Rejected (same guard) |
| Atomic? | Yes — item insert + totals refresh + commit occur in the same request (pre-existing, unmodified) |
| Audit evidence? | **Not found** — `add_item` does not call `_log_event`/`_pkg_audit`-equivalent for item additions (unlike `create_invoice`, `issue_invoice`, `cancel_invoice`, which do). This is a pre-existing gap, not introduced this slice; not fixed (see `known-limitations.md`) since choosing the event-name/payload convention is a small design decision, not a mechanical fix, mirroring the same disposition given to `package_commerce`'s equivalent audit gaps in Slice 2F-5C. |

## Direct tests (see `tests/test_phase2f6a_invoice_payment_integrity.py`)
Negative quantity rejected; zero quantity rejected; negative unit_price
rejected; zero unit_price allowed; double-negative rejected; item added
after issue/full-payment/cancellation rejected; valid item addition
succeeds; cross-tenant item addition rejected with no mutation.

## Conclusion
The conclusively-provable defect (unvalidated negative/zero quantity and
negative unit_price) is fixed by rejection, not by inventing a discount
system. The pre-existing audit-coverage gap for item additions is
documented as a known limitation, not fixed.
