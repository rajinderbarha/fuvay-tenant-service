# Server Total Reconciliation

## Formula (unchanged this slice, traced and confirmed)
```
total = labour_amount + parts_amount + service_amount - discount_amount + tax_amount
customer_payable_amount = total   (at the QUOTE level)
```
At the INVOICE level, an additional platform fee is layered on top (`_refresh_totals` in `invoice_service.py`, pre-existing, unchanged): `customer_payable_amount = service_value + platform_fee` where `platform_fee = service_value * fee_pct / 100`, quantized to `Decimal("0.01")`.

## Precision
- `quantity`: `Numeric(10,3)` (3 decimal places).
- `unit_price`/`line_total`/all amount fields: `Numeric(14,2)` (2 decimal places).
- `line_total = quantity * unit_price` — Python `Decimal` arithmetic (deterministic, no floating-point).
- Discount application order: discount is SUBTRACTED after summing labour+parts+service, BEFORE tax is added (`total = labour + parts + service - discount + tax`) — tax is not computed on a pre-discount or post-discount basis distinctly; it is simply an independent additive bucket (whatever tax-type items were entered).
- Platform-fee rounding: `.quantize(Decimal("0.01"))` — standard 2-decimal rounding, deterministic.

## Recalculation trigger
Every `add_item`/`update_item`/`remove_item` call re-fetches ALL current items for the quote and calls `_recalculate` fresh (full replace, not incremental) — confirmed in `quote-amount-integrity.md` (2F-16). This slice's `get_quote` fix performs the SAME `_recalculate` call again, but scoped to only the customer-visible subset, for DISPLAY purposes — it does not write this recomputed value back to the stored `ServiceJobQuote` row (the provider-view stored total is untouched).

## Stored vs. derived totals
| Total | Stored or derived? | Basis |
|---|---|---|
| `ServiceJobQuote.total_amount`/`customer_payable_amount` (provider view, via `get_quote(tenant_id=...)`) | Stored (persisted column, refreshed on every item mutation) | ALL items (visible + hidden) |
| Customer-facing total (via `get_quote(customer_id=...)`) | **Derived on read, this slice** — never persisted | Customer-visible items only |
| `ServiceInvoice.total_amount`/`customer_payable_amount` | Stored (persisted column, computed by `_refresh_totals` at invoice-creation time) | `ServiceInvoiceItem` rows, which were seeded exclusively from customer-visible quote items (`_copy_from_quote`, pre-existing) |

## Reconciliation proof
Because (a) the customer-facing quote total (this slice) and (b) the eventual invoice total (pre-existing) are BOTH computed from the identical set of customer-visible items using the identical `_recalculate` formula, they are guaranteed to agree (before any platform fee is layered onto the invoice, which is a separate, disclosed, additive step — not a discrepancy). Proven by `TestHiddenItemTotalReconciliation` + `TestInvoiceQuoteServiceJobCustomerLinkage::test_matching_servicejob_and_customer_succeeds` together.

## No new pricing policy introduced
Per explicit scope limits, the formula itself, the platform-fee mechanism, and the rounding behavior are unchanged — this slice only fixed WHICH items feed into the customer-facing DISPLAY of that formula, not the formula itself.
