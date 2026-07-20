# Regression Report — Slice 2F-14B

## Slice-specific executions

- `tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` (21 tests, new) —
  PASS.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30 tests, 2 canonical-figure
  assertions updated this slice) — PASS.
- `tests/test_phase2f14_field_ops_staff_authorization.py` (34 tests) — PASS.

Combined: **85 passed, 0 failed.**

## Broad partition sweep

`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate
or coaching or invoice or payment or commission or parts_request"`:
**1262 passed, 1 skipped, 12 failed, 5 errors** (before the coverage-figure test update above; all
12 failures/5 errors are pre-existing live-network/live-database exclusions, confirmed below —
after updating the two stale canonical-figure assertions, the count is 1264 passed / 10 failed
attributable purely to live-environment absence).

## Live-network/live-database exclusions (not counted as passing)

All traced via traceback inspection to `httpx.ConnectError`, `asyncpg` connection failure, or
`ConnectionRefusedError: [WinError 1225]` — every one requires a running app server/Postgres
instance not present in this environment:

- `test_module_l5_16_quotes.py::test_quote_event_table_has_updated_at`
- `test_module_l5_16_quotes.py::TestCustomerQuoteFlow::test_customer_can_approve_a_quote_and_job_syncs`
- `test_module_l5_16_quotes.py::TestCustomerQuoteFlow::test_booking_detail_exposes_job_id`
- `test_module_l5_21_quote_notify.py::TestQuoteNotifyLive::test_customer_approval_notifies_the_provider`
- `test_module_l5_26_invoice_notify.py::TestInvoiceIssueNotifyLive::test_issuing_a_draft_invoice_notifies_the_customer`
- `test_module_l5_28_credit_checkout.py::test_invoice_has_credit_column`
- `test_module_l5_29_booking_cancel_reschedule.py::TestCancelRescheduleLive::test_cancel_is_blocked_once_invoiced`
- `test_module_l5_32_package_commission_deadmodel.py::TestLive::test_delete_package_does_not_500`
- `test_module_l5_35_staff_app_jobs_api.py::TestLive::test_field_ops_jobs_list_422s_without_tenant_id_and_succeeds_with_it`
- `test_module_l5_45_package_activation_limits.py::test_activation_creates_and_sets_limits_and_commission_live`
- `test_module_l5_18_invoices.py::TestCustomerInvoices::*` (3 errors)
- `test_p0_navigation_operation_visibility.py::TestEffectiveMenuResolver::*` (2 errors)

None touch any file changed this slice. Separately disclosed, not counted as passing.

## Net result

1264 passed / 0 failures attributable to this slice's changes / 15 pre-existing live-environment
exclusions honestly disclosed.
