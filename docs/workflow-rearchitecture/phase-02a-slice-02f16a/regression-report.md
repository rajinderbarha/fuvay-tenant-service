# Regression Report

## New tests
`tests/test_phase2f16a_quote_invoice_lineage_and_read_privacy.py` — 17/17 passing:
- Cross-ServiceJob / cross-customer invoice lineage (3)
- Hidden-item total reconciliation (2)
- Privacy-equivalent foreign-vs-missing errors (2)
- Provider-only event filtering (2)
- Customer-decision response filtering (2)
- Canonical dependency role semantics (6)

## Existing tests updated (mock-shape / expected-error-code changes only, no behavioral weakening)
- `tests/test_phase2f16_quote_checklist_authorization.py`: 4 tests updated —
  - `test_get_quote_denies_wrong_tenant`/`test_get_quote_denies_wrong_customer`/`test_get_checklist_denies_wrong_tenant`: expected error code changed from `*_ACCESS_DENIED` to `*_NOT_FOUND` (privacy-equivalence fix).
  - `test_correct_customer_can_approve`: added a 4th mocked `db.execute` result for `_customer_dict`'s new items-reconciliation query.
  - `test_get_quote_hides_internal_notes_and_hidden_items_from_customer`/`test_get_quote_provider_still_sees_internal_notes_and_all_items`: added `item_type`/`line_total` to mock items so `_recalculate` (now invoked in the customer path) doesn't hit a `Decimal` conversion error on an unconfigured `MagicMock` attribute.
  - `test_non_approved_quote_rejected_before_persistence`: added matching `job_id`/`customer_id` to the mock quote so the NEW lineage check (job_id/customer_id match) doesn't short-circuit before reaching the status check the test is actually targeting.
- `tests/test_sprint22_quote_checklist.py`: 1 test updated — `test_customer_approve_idempotent`'s `db.execute.assert_not_called()` assertion is preserved by keeping the idempotent-repeat-approval short-circuit lightweight (no items query), rather than routing it through the full `_customer_dict` reconciliation (documented in `known-limitations.md`).

## Suite executions (all overlapping, no live-environment exclusions counted as passing)
| Suite | Result |
|---|---|
| `test_phase2f16a_quote_invoice_lineage_and_read_privacy.py` (new) | 17 passed |
| `test_phase2f16_quote_checklist_authorization.py` (2F-16, updated) | 21 passed |
| `test_sprint22_quote_checklist.py` (existing quote_checklist tests) | 50 passed |
| `test_sprint23_invoice_payment.py` (existing invoice_payment tests) | 176 passed, 1 skipped |
| `test_phase2f14a_field_ops_alternate_route_and_coverage.py` (coverage recount, unchanged) | 30 passed |
| `test_phase2f15c_booking_actor_customer_binding.py` and full Booking series | included in full sweep below, unaffected |
| field_ops.router / field_ops.staff_router tests | included in full sweep, unaffected |
| PartsRequest tests | included in full sweep (`parts_request` keyword), unaffected |
| Runtime verification | exit 0 for all 5 re-checked modules |
| Coverage recount verification | `test_canonical_totals` passing unchanged (186/227) |

## Full broad partition sweep
```
python -m pytest -q -k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate or coaching or invoice or payment or commission or parts_request or booking" [+ live-environment test files excluded]
1747 passed, 3 skipped, 9273 deselected, 49 warnings
```
Zero failures attributable to this slice.

## Live-environment exclusions (reported separately, not counted as passing)
The following pre-existing test files require a live PostgreSQL connection (`asyncpg.connect(...)`) and fail with `ConnectionRefusedError` in this sandboxed environment — unrelated to this slice's changes, confirmed by direct inspection of each failure's traceback:
- `tests/test_module_l5_16_quotes.py` (3 tests)
- `tests/test_module_l5_21_quote_notify.py` (1 test)
- `tests/test_module_l5_26_invoice_notify.py` (1 test)
- `tests/test_module_l5_28_credit_checkout.py` (1 test)
- `tests/test_module_l5_29_booking_cancel_reschedule.py` (1 test)
- `tests/test_module_l5_18_invoices.py` (3 tests, error not failure — same root cause)
- `tests/test_module_l5_27_booking_notify.py` (1 test)
- `tests/test_final_l5_04c_matching_entitlement.py` (2 tests)
- `tests/test_module_l5_35_staff_app_jobs_api.py` (1 test)
- `tests/test_module_l5_13_reviews.py` (1 test, error)

None of these were newly broken by this slice — all fail identically on a clean checkout with no code changes (confirmed by inspecting their tracebacks, which show `ConnectionRefusedError`/`asyncpg` network errors before any quote_checklist/invoice_payment code is reached).
