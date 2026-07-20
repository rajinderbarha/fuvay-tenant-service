# Quote Service-Layer Bypass Report

## Service methods audited
`ServiceJobQuoteService` (create_quote, add_item, update_item, remove_item, send_to_customer, customer_approve, customer_reject, customer_request_revision, cancel_quote, get_quote, list_quotes_for_job, list_customer_quotes, list_quote_events, mark_revised) and `ServiceChecklistService` (create_template, add_template_item, list_templates, get_template, create_checklist, update_checklist_item, complete_checklist, get_checklist, list_checklists_for_job).

## Callers enumerated
- **API callers**: `provider_router.py` (provider_router/staff_router/checklist_router), `customer_router.py`, `admin_router.py` — all 3 modules, every route inventoried in `quote-checklist-final-route-inventory.csv`.
- **Internal/worker callers**: `invoice_payment.invoice_service._copy_from_quote` (reads `ServiceJobQuoteItem` only, never calls into `ServiceJobQuoteService`/`ServiceChecklistService` methods directly — a raw query, not a service-layer call). No background/worker scheduler calls any quote_checklist service method.

## Strongest / weakest caller
- **Strongest**: `admin_router.py` (`require_super_admin`, intentionally bypasses tenant/customer ownership — platform-only, correct by design).
- **Weakest (before this slice)**: every mutation route in `provider_router.py`/`customer_router.py` — `get_current_user` only, no persona/permission/ownership enforcement at the router layer, and `get_quote`/`get_checklist` had no ownership enforcement at the SERVICE layer either (router authorization does not replace object ownership — this was doubly weak). **Fixed this slice.**
- **Weakest (found and fixed this slice, different module)**: `invoice_payment.invoice_service.create_invoice`'s `source="approved_quote"` path — no tenant/status validation on the referenced quote before copying its items. **Fixed this slice** (see `quote-financial-boundary.md`).

## Per-method verification
| Method | Tenant source | Customer source | Job/execution ownership | Quote/item ownership | State validation | Amount calc | Financial effects | Transaction ordering | Audit actor | Notification |
|---|---|---|---|---|---|---|---|---|---|---|
| `create_quote` | `tenant_id` param (now server-derived at router via `require_owner_or_office_staff_mutation`) | n/a | `job.tenant_id == tenant_id` (pre-existing) | n/a (new record) | n/a | n/a (items added later) | none | add → flush → log_event → commit (unchanged) | `user_id` param (server-derived) | none |
| `add_item`/`update_item`/`remove_item` | `_assert_tenant` | n/a | via quote's own tenant | compound `id == item_id AND quote_id == q.id` (pre-existing) | **new this slice**: `ITEM_EDITABLE_QUOTE_STATUSES` | server-computed `line_total`, **negative validation added this slice** | none | validate → mutate → recalc → log_event → commit | `user_id` param | none |
| `send_to_customer` | `_assert_tenant` | n/a | via quote | `_assert_transition` (pre-existing) | pre-existing | n/a | none | validate → update → sync job → log_event → notify → commit | `user_id` param | `notify_customer_quote_sent` |
| `customer_approve`/`reject`/`request_revision` | n/a | `quote.customer_id == customer_id` (pre-existing, re-verified) | via quote | `_assert_transition` | pre-existing | n/a (no amount input accepted) | none | validate → update → sync job → log_event → notify → commit | `user_id` = caller's own (server-derived) | `notify_provider_quote_decision` |
| `get_quote`/`get_checklist`/`list_quote_events` | **new this slice**: `tenant_id`/`customer_id` params enforced | same | n/a (read-only) | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| `create_checklist` | `tenant_id` param | n/a | **new this slice**: job lookup + `job.tenant_id == tenant_id` | n/a (new record) | n/a | n/a | none | validate → add → commit | `user_id` param | none |
| `update_checklist_item`/`complete_checklist` | `_assert(cl.tenant_id == tenant_id)` (pre-existing) | n/a | via checklist | compound `id == item_id AND checklist_id == cl.id` (pre-existing) | `CL_COMPLETED` guard (pre-existing) | n/a | none | validate → mutate → commit | `user_id` param | none |

## Bypasses closed this slice
1. Router-level authorization (provider/staff/checklist/customer routers) — see `provider-quote-authorization.md`/`customer-quote-decision-authorization.md`.
2. `get_quote`/`get_checklist`/`list_quote_events` ownership (IDOR) — see `quote-job-item-ownership.md`.
3. `create_checklist` job/tenant ownership — see `quote-job-item-ownership.md`.
4. Negative amount validation — see `quote-amount-integrity.md`.
5. Post-final/post-send item mutation lock — see `quote-amount-integrity.md`.
6. `invoice_payment.create_invoice`'s cross-tenant/wrong-status quote copy — see `quote-financial-boundary.md`.

No other directly-connected bypass was found. Router authorization now correctly complements (not replaces) the object-ownership checks already present at the service layer.
