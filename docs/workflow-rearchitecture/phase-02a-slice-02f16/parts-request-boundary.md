# PartsRequest Boundary

## Finding
Repo-wide search within `app/engines/quote_checklist/*.py` for `PartsRequest` returns **no matches**. `ServiceJobQuoteItem.item_type` includes `"part"` and `"material"` as valid cost-line categories (contributing to `parts_amount` in `_recalculate`), but these are plain cost-line entries — a string `item_type`, an `item_name`, a `quantity`/`unit_price` — with **no foreign key, no ID reference, and no service-layer call** to the `PartsRequest` model or its approval/install workflow anywhere.

## Classification
**DISCONNECTED** — there is no relationship of any kind between quote_checklist's "part"/"material" line items and the actual `PartsRequest` approval/installation record. They independently represent the same real-world concept (parts cost) in two completely separate systems with no data linkage.

## Preserved (unaffected by this slice)
- `PartsRequest` remains ServiceJob-only (unchanged, not touched).
- Technician may request/view parts (unchanged, not touched — this is a `PartsRequest`-specific capability, no route in `quote_checklist` overlaps it).
- Provider approves/rejects/installs parts (unchanged, not touched).
- Technician may not install parts (unchanged, not touched).
- Customer quote approval (`quote_checklist`) remains entirely distinct from `PartsRequest`'s own approval workflow — a customer approving a `ServiceJobQuote` that happens to contain a "part" line item does **not** approve, reject, or install any `PartsRequest` row. No code path connects the two.

## No action required
Since no code path links quote approval to `PartsRequest` mutation, there is nothing to fix here — this boundary was already correctly disconnected before this slice, and remains so.
