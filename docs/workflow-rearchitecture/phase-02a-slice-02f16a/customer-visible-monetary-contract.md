# Customer-Visible Monetary Contract

| Item type | Customer visible? | Billable? | In subtotal | In tax basis | In discount basis | In final total | In Invoice | Editable after send | Editable after approval |
|---|---|---|---|---|---|---|---|---|---|
| `labour` | Depends on `is_customer_visible` flag | If visible | yes | yes | yes | yes | Only if `is_customer_visible=True` | no (this slice's `ITEM_EDITABLE_QUOTE_STATUSES` lock) | no (locked) |
| `part`/`material` | Same | Same | yes | yes | yes | yes | Only if visible | no | no |
| `service` | Same | Same | yes | yes | yes | yes | Only if visible | no | no |
| `discount` | Same | Reduces total, not itself "billable" | Subtracted | n/a | n/a | yes (subtracted) | Only if visible | no | no |
| `tax` | Same | Added to total | Added | n/a | n/a | yes (added) | Only if visible | no | no |
| `visit_charge` | Same | If visible | yes (falls through `_recalculate`'s `elif` chain — see `known-limitations.md`) | n/a | n/a | Only if it matches a recognized `item_type` bucket | Only if visible | no | no |
| `other` | Same | If visible | Same caveat as `visit_charge` | n/a | n/a | Same caveat | Only if visible | no | no |

## Classification per field
- `is_customer_visible=True` items → **CUSTOMER_VISIBLE_BILLABLE** (or non-billable if `item_type` doesn't map into `_recalculate`'s buckets — see below).
- `is_customer_visible=False` items → **PROVIDER_INTERNAL_COST_REFERENCE** or **PROVIDER_INTERNAL_MARGIN** depending on intent (the schema does not distinguish "internal cost" from "internal margin padding" — both are simply `is_customer_visible=False`, a single boolean, not a typed classification). This is a known limitation, not fixed (would require a new field/enum — schema change, out of scope).
- `provider_internal_notes` (quote-level, not item-level) → **PROVIDER_INTERNAL_NON_BILLABLE** — free text, never contributes to any total, correctly stripped from customer reads this slice's predecessor (2F-16) already achieved; re-verified unaffected.

## Requirement: a provider-internal item must not increase customer payable amount unless explicitly represented
**Satisfied, this slice.** Before this slice, a hidden item's cost WAS silently folded into the customer-visible `total_amount`/`customer_payable_amount` shown by `get_quote` (INTEGRITY_DEFECT — see `hidden-item-total-test-matrix.csv`). Fixed: the customer-facing total is now recomputed from only customer-visible items (`get_quote`'s `customer_totals = self._recalculate(rows)` where `rows` has already been filtered to `is_customer_visible == True`).

## `_recalculate`'s bucket coverage caveat (pre-existing, not introduced this slice)
`_recalculate` only accumulates `item_type` values it explicitly recognizes (`labour`, `part`/`material`, `service`, `discount`, `tax`) into the total formula (`labour + parts + service - discount + tax`) — `visit_charge` and `other` item types are NOT summed into any bucket, meaning an item with `item_type="visit_charge"` or `"other"` contributes ZERO to the displayed/invoiced total even though it appears in the `items` list with its own non-zero `line_total`. This is a genuine pre-existing gap (not introduced or worsened by this slice) — documented honestly in `known-limitations.md`, not fixed (would require deciding new pricing-bucket policy, explicitly out of scope: "Do not introduce a new pricing policy").
