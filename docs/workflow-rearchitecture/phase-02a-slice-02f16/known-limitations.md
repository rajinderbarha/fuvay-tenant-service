# Known Limitations

- No live database/server verification was performed (unit tests + static/executed route introspection only), consistent with every prior slice in this initiative.
- `QUOTE_NOT_FOUND` and `QUOTE_ACCESS_DENIED` remain distinguishable error codes — a caller can tell "no such quote" from "quote exists but isn't yours." Narrower privacy property than the Booking series' uniform-error pattern; not changed (see `product-decisions-required.md`).
- No database-level uniqueness constraint prevents duplicate line items with identical `(quote_id, item_name, item_type)` — application-level only, and arguably not a defect (legitimate duplicate parts orders look identical to accidental duplicates at the data level).
- No optimistic-concurrency versioning on `ServiceJobQuote` — concurrent edits by two authorized staff members race on the recalculated total (last-write-wins). Documented in `duplicate-concurrency-review.md`, not fixed (would require a schema change).
- Quote expiry (`QS_EXPIRED`) is unreachable — no writer exists. Documented, not built (would require inventing new automation policy, out of scope).
- Technician quote-input capability was NOT granted (deliberately) — if a future technician-facing UI is built for quote line items, `require_owner_or_office_staff_mutation` would need to be reconsidered against new evidence, per the same reasoning that excluded it this slice.
