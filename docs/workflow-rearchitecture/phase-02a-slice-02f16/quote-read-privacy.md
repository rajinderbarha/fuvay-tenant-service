# Quote/Checklist Read and Privacy

| Read surface | Tenant isolation | Customer ownership | Technician filtering | Internal-cost hiding | Public exposure |
|---|---|---|---|---|---|
| Provider quote list/detail | `tenant_id` filter (list, pre-existing) / `tenant_id` ownership (detail, **fixed this slice**) | n/a | No technician caller exists for this route (see `provider-quote-authorization.md`) | `provider_internal_notes` visible to provider/staff (correct — it's their own field) | No public route exists |
| Customer quote detail | n/a | `customer_id` ownership (**fixed this slice**) | n/a | **Fixed this slice**: `get_quote` strips `provider_internal_notes` whenever `customer_id` is supplied | No public route |
| Quote items | Via parent quote's tenant/customer ownership | Same | Same | **Fixed this slice**: `get_quote` filters out `is_customer_visible=False` items whenever `customer_id` is supplied | No public route |
| Quote history/events | `tenant_id`/`customer_id` filter (**customer_id enforcement added this slice**) | Same | n/a | n/a | No public route |
| Checklist answers | `tenant_id` ownership (**fixed this slice**) | n/a (no customer-facing checklist route exists) | No technician caller found | n/a | No public route |
| Rejection reasons | Via parent quote ownership | Same | n/a | n/a | No public route |
| Evidence/media references (`ServiceJobChecklistItem.media_url`) | Via parent checklist ownership | n/a | n/a | n/a | No public route |

## GET routes produce no mutation
Confirmed for every GET route in `quote-checklist-final-route-inventory.csv` — none call `db.add`/`db.execute(update(...))`/`db.execute(delete(...))`.

## Provider-internal fields now private (fixed this slice)
`get_quote`'s new `customer_id is not None` branch strips `provider_internal_notes` from the returned dict and filters the items list to `is_customer_visible == True` only — both proven by direct test (`test_get_quote_hides_internal_notes_and_hidden_items_from_customer`) and confirmed unaffected for the provider/staff/admin path (`test_get_quote_provider_still_sees_internal_notes_and_all_items`, `tenant_id`-scoped calls are unaffected).

## Foreign IDs do not reveal record existence
`QUOTE_NOT_FOUND` vs `QUOTE_ACCESS_DENIED` ARE distinguishable error codes (unlike some other closed modules' single uniform error) — a caller CAN currently tell the difference between "no such quote" and "quote exists but isn't yours." This is a narrower privacy property than the Booking series' single uniform error pattern. Not changed this slice (would require altering an established, tested error-code contract that existing frontend code may depend on — judged out of proportion to fix without direct evidence of exploitation value, since the underlying record's CONTENT is still never disclosed either way — see `known-limitations.md`).
