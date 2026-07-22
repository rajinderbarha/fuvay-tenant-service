# No-Partial-Persistence Proof

| Rejection | Test | Proof |
|---|---|---|
| Cross-ServiceJob Quote (same tenant) | `test_quote_from_different_servicejob_same_tenant_rejected` | `db.add.assert_not_called()` — validation runs BEFORE `db.add(inv)` |
| Cross-customer Quote (same tenant, same job_id) | `test_quote_for_different_customer_same_tenant_same_job_id_rejected` | `db.add.assert_not_called()` |
| Unapproved Quote | `test_non_approved_quote_rejected_before_persistence` (2F-16, updated) | `db.add.assert_not_called()` |
| Cross-tenant Quote | `test_wrong_tenant_quote_rejected_before_persistence` (2F-16) | `db.add.assert_not_called()` |
| Hidden-item total mismatch (read path) | N/A — not a mutation; `get_quote` never calls `db.add` at all (read-only method) | Confirmed by source read |
| Foreign customer/tenant read (Quote/checklist) | `test_get_quote_missing_and_foreign_tenant_raise_same_code` / `test_get_checklist_missing_and_foreign_tenant_raise_same_code` | Raises immediately after the ownership comparison, before any items/events query |
| Final-state mutation (item edit after send/terminal) | `test_add_item_after_sent_to_customer_rejected` / `test_remove_item_after_customer_rejected_status_blocked` (2F-16, unaffected, re-verified) | `db.add.assert_not_called()` |
| Invalid role/alias (`office_staff`, etc.) | `test_denies_prohibited_aliases` | Raises at the FastAPI dependency layer — the route handler body (and therefore any service method) is never entered |
| Read-only tenant mutation attempt | `test_denies_readonly_access_scope` | Same — denied at the dependency layer |

## Source-position confirmation
- `create_invoice`: the new `quote.job_id`/`quote.customer_id` checks are positioned immediately after the (pre-existing) tenant check and BEFORE the `ServiceInvoice(...)` constructor call and `db.add(inv)` — confirmed by direct code read (see `exact-invoice-creation-contract.md`).
- `get_quote`/`get_checklist`/`list_quote_events`: read-only methods; no persistence exists to partially commit in the first place.
- `customer_approve`/`customer_reject`: the `_customer_dict` privacy/reconciliation helper runs AFTER all mutation/persistence logic (it is the final step before `return`), so it cannot itself cause partial persistence — it only reads.

## No Job/history/financial side effect on any rejection
Every rejected scenario above raises before reaching `_log_event`/`_sync_job_status`/`notify_*`/invoice-creation calls, unchanged in source order from before this slice (only new EARLIER guards were added, never reordering existing downstream effects).
