# Invoice Source Authority

`VALID_INVOICE_SOURCES` (unchanged this slice): `approved_quote`, `booking_base`, `manual_final` (exact constant names per `app/engines/invoice_payment/constants.py`).

## `approved_quote` (this slice's focus)
Fully validated this slice — see `quote-servicejob-customer-lineage.md`. Items derive exclusively from `ServiceJobQuoteItem` rows belonging to the exact, approved, same-tenant, same-ServiceJob, same-customer quote.

## `booking_base`
Out of scope this slice (no Quote involvement — copies from `ServiceBooking`, a different pipeline entirely; not touched).

## `manual_final`
Out of scope this slice (no Quote involvement — staff manually enters invoice items directly; not touched).

## No client-supplied amount override
`create_invoice`'s signature accepts no amount/total field at all — `_refresh_totals` is the sole author of every monetary field on the invoice, computed server-side from the copied items (unchanged, pre-existing, re-verified this slice via full regression).
