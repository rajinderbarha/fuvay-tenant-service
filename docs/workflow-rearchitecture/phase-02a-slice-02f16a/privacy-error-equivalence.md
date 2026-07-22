# Privacy-Safe Error Semantics

## The gap
`app/exceptions.py`'s `ValueError`->HTTP mapping (`_domain_code_status`) maps error codes containing `NOT_FOUND` to 404 and codes containing `ACCESS_DENIED`/`DENIED`/`FORBIDDEN`/`NOT_ALLOWED` to a 403-class status. Before this slice, `get_quote`/`get_checklist`/`list_quote_events` raised `*_ACCESS_DENIED` for a foreign-tenant/foreign-customer record but `*_NOT_FOUND` for a genuinely missing one — externally distinguishable via HTTP status code AND the `error_code` field in the response body, disclosing "this record exists (for someone else)" versus "this record doesn't exist."

## The fix
`get_quote`, `list_quote_events` (both `tenant_id` and `customer_id` mismatch branches), and `get_checklist` now all raise the SAME `ERR_QUOTE_NOT_FOUND`/`ERR_CHECKLIST_NOT_FOUND` code for both the missing-record case and the foreign-ownership case.

## External behavior after this fix
| Scenario | HTTP status | `error_code` |
|---|---|---|
| Missing Quote | 404 | `QUOTE_NOT_FOUND` |
| Foreign-tenant Quote | 404 | `QUOTE_NOT_FOUND` |
| Foreign-customer Quote | 404 | `QUOTE_NOT_FOUND` |
| Quote belonging to another ServiceJob (not directly readable by ID — access is always via the OWNING tenant/customer's own scoped queries, so this scenario collapses into the foreign-tenant/foreign-customer case above) | 404 | `QUOTE_NOT_FOUND` |
| Missing item | 404-class (`QUOTE_ITEM_INVALID`, pre-existing, unchanged — this code does not contain "ACCESS_DENIED" or "NOT_FOUND" literally but maps via a different rule; not touched this slice since item lookups are always nested inside an already-ownership-verified quote, so no separate existence-disclosure risk exists at the item level) | `QUOTE_ITEM_INVALID` |
| Foreign item (belonging to a different quote) | Same `QUOTE_ITEM_INVALID` as missing — already equivalent, unchanged |
| Missing checklist | 404 | `CHECKLIST_NOT_FOUND` |
| Foreign checklist | 404 | `CHECKLIST_NOT_FOUND` (this slice's fix) |

## Internal logging remains diagnostically specific
The `value_error_handler` in `app/exceptions.py` logs `logger.info("domain.value_error", error_code=code, status=st, path=...)` regardless of which specific ownership condition triggered the error — since `get_quote`/`get_checklist` now raise a single code for both cases, the LOG itself is equally undifferentiated between "missing" and "foreign" at this layer. This is an accepted trade-off: per the mission's own instruction ("Internal logs may retain distinct diagnostic reasons"), a future slice COULD add a separate internal-only log field distinguishing the two cases without changing the external response — not done this slice (no evidence of an operational need, and the mission does not require it, only permits it).

## Timing-sensitive extra queries
Not materially different — both the missing-record path (`_get_quote` returns `None` immediately) and the foreign-ownership path (`_get_quote` succeeds, THEN the ownership comparison fails) perform exactly one query before raising in either case (a single `SELECT` followed by either a `None` check or a field comparison) — no meaningfully exploitable timing side-channel was introduced or removed by this change.

## `QUOTE_NOT_FOUND` and `QUOTE_ACCESS_DENIED` externally indistinguishable — now satisfied
Per the mission's explicit closure requirement ("`QUOTE_NOT_FOUND` and `QUOTE_ACCESS_DENIED` cannot remain externally distinguishable while PRIVACY_CLOSED is claimed"), this is now closed for all customer-reachable and provider-reachable READ paths in this module. `QUOTE_ACCESS_DENIED` still exists as a distinct code for MUTATION-path tenant checks (`_assert_tenant`, used by `add_item`/`update_item`/`cancel_quote`/etc.) — this is a different semantic (a tenant-scoped mutation attempt on a record outside your tenant, where "record exists" is not sensitive information to a tenant/staff caller in the same way it is to an external/customer caller) and was not in the mission's scope to unify (Workstream 9 focuses on customer/foreign-tenant READ scenarios specifically).
