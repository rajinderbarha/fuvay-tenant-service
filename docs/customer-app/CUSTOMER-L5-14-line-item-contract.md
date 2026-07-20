# CUSTOMER-L5-14 — Quote Line Item Contract

`ServiceJobQuoteItem` (`app/engines/quote_checklist/models.py` lines
82–117), table `service_job_quote_items`.

## Fields

`id`, `quote_id`, `booking_id`, `job_id`, `tenant_id`, `item_type`
(`labour`/`part`/`material`/`service`/`visit_charge`/`discount`/`tax`/
`other` — `constants.py` lines 44–56), `item_name`, `item_description`,
`quantity` (`Numeric(10,3)`), `unit_price`, `line_total`, `is_required`,
`is_customer_visible`, `item_metadata` (JSONB).

## Server-side computation (`quote_service.py` `_recalculate`, lines 104–122)

`line_total = quantity * unit_price`, computed server-side on
`add_item`/`update_item`/`remove_item` (staff-only endpoints). This
client never recomputes it — always renders `line_total` exactly as
returned, matching the app-wide money-handling rule.

`labour_amount`/`parts_amount`/`service_amount`/`discount_amount`/
`tax_amount` on the parent quote are each a sum over items of the
matching `item_type` (labour → `labour_amount`; `part`/`material` both
roll into `parts_amount`; `service` → `service_amount`; `discount` →
`discount_amount`, subtracted in the total; `tax` → `tax_amount`, added).
`total_amount = labour + parts + service - discount + tax`;
`customer_payable_amount` is currently always set equal to
`total_amount` (no separate deposit/partial-payment concept exists).

## Customer visibility — real, disclosed gap

`is_customer_visible` is a real column meant to let a provider include
an item in their own internal total without showing it to the customer
(e.g. an internal margin line). `GET /customer/quotes/{quote_id}`
(`get_quote`, `quote_service.py` lines 452–460) returns **every** item
regardless of this flag — the server does not filter. This client's
`parseQuoteDetail` (`domain/quote-schema.ts`) drops any item where
`is_customer_visible !== true` after validation, so a non-visible item
is never rendered even though the raw response includes it. Covered by
`quote-schema.test.ts`'s "filters out items not flagged
is_customer_visible" case.

## Fields this client never renders

`is_required` (server-side only concept — this client doesn't offer
per-item selective approval; approval/rejection/revision always applies
to the whole quote, matching the real endpoints, which operate on
`quote_id`, never `item_id`), `item_metadata` (opaque, no defined shape
in any source file read this sprint).
