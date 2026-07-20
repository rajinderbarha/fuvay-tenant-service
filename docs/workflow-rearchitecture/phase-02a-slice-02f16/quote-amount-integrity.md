# Quote Amount and Total Integrity

## How totals are computed
`ServiceJobQuoteService._recalculate(items)` (unchanged this slice, verified correct) sums each `ServiceJobQuoteItem.line_total` into a bucket keyed by `item_type` (labour/parts/service/discount/tax), then:
```
total = labour + parts + service - discount + tax
customer_payable_amount = total
```
This is recomputed from the FULL current set of items every time `add_item`/`update_item`/`remove_item` is called (`select(...).where(quote_id == q.id)` re-fetches all items, not an incremental update) — this means deleted line items cannot remain in the total (they're excluded from the re-fetch), and repeated calculation does not duplicate totals (it's a full replace via `update(...).values(**totals)`, not an increment).

## Server calculates, never trusts client totals
- `line_total = quantity * unit_price`, computed server-side in `add_item`/`update_item` — the client supplies `quantity`/`unit_price` (raw numbers) but never `line_total` or the quote's own `total_amount` directly.
- The customer decision payload (`approve`/`reject`/`request-revision`) carries NO amount field at all — `customer_approve` accepts only `idempotency_key`; `customer_reject`/`customer_request_revision` accept only `reason`. **Customer cannot edit provider prices or influence the total in any way.**
- The provider CAN submit item quantity/unit_price directly (this is the intended manual-pricing model — no separate "pricing engine" exists or is built this slice, per the explicit out-of-scope instruction). There is no "client-supplied total" field on the quote itself that could be inconsistent with line items — `total_amount` is exclusively server-computed, never accepted as router input.

## Negative quantity/price — fixed this slice
Previously unvalidated. `add_item` and `update_item` now reject `quantity < 0` or `unit_price < 0` with `QUOTE_ITEM_INVALID`, before any persistence. A "negative discount" (which would perversely INCREASE the total when subtracted) is excluded by this same non-negative constraint — discount items reduce the total via `_recalculate`'s subtraction, not via a negative unit_price trick.

## Excessive discount behavior
No maximum-discount cap exists or is enforced — a discount item's `unit_price * quantity` can equal or exceed the sum of all other line items, driving `total_amount` to zero or (if discount exceeds other items) negative. This is NOT fixed this slice (would require inventing a new pricing policy, explicitly out of scope) — documented honestly in `known-limitations.md`/`product-decisions-required.md` as an unresolved product question, not a security defect (the discount amount is still fully server-computed and auditable via `ServiceJobQuoteEvent`).

## Currency
Hardcoded `"INR"` at creation (`create_quote`) — no per-tenant or per-item currency field, no multi-currency support. Consistent throughout a single quote by construction (never varies per item).

## Rounding
`Numeric(14,2)` for all amount columns, `Numeric(10,3)` for quantity — standard SQL `NUMERIC` fixed-point arithmetic, deterministic (no floating-point summation occurs at the database level; Python-side `Decimal` arithmetic is used in `_recalculate`, also deterministic).

## Final-state immutability
`locked_at` is set only by `customer_approve` — this was the ONLY mechanism preventing post-final edits before this slice, and it left `sent_to_customer` (customer actively deciding) and every OTHER terminal status (rejected/expired/cancelled) editable. Fixed this slice: `add_item`/`update_item`/`remove_item` now additionally require `q.status in ITEM_EDITABLE_QUOTE_STATUSES` (draft/submitted_to_provider/provider_rejected/revision_requested/revised) — `sent_to_customer` and every terminal status now correctly block item mutation.

## Rejected quote does not produce an invoice; approval does not fabricate payment
No invoice/payment code exists anywhere in this module (see `quote-financial-boundary.md`) — trivially true since there is no capability to build upon.
