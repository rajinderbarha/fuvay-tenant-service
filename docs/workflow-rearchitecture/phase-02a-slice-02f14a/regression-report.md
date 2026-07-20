# Regression Report

## Slice-specific executions

- `tests/test_phase2f14_field_ops_staff_authorization.py` (34 tests) — PASS, re-run this slice.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30 tests, new) — PASS.
- `tests/test_step8_quote_checklist.py` — PASS.
- `tests/test_p0_job_completion_credit_deduction.py` — PASS.
- `tests/test_phase2f13_checklist_template_authorization.py` — PASS.

Combined: **192 passed, 0 failed.**

## Broad partition sweep

`-k "field_ops or checklist or step8 or job_type or complaints or real_estate or coaching or
invoice or payment or commission or parts_request or quote_checklist"`:
**1226 passed, 1 skipped, 6 failed, 5 errors** (out of 1233 collected + deselected others).

## Live-network/live-database exclusions (not counted as passing)

All 6 failures and 5 errors traced via traceback inspection to
`httpx.ConnectError: All connection attempts failed` or
`ConnectionRefusedError: [WinError 1225]` — every one requires a running app server/database that
is not present in this environment:

- `test_module_l5_26_invoice_notify.py::TestInvoiceIssueNotifyLive::test_issuing_a_draft_invoice_notifies_the_customer`
- `test_module_l5_28_credit_checkout.py::test_invoice_has_credit_column`
- `test_module_l5_29_booking_cancel_reschedule.py::TestCancelRescheduleLive::test_cancel_is_blocked_once_invoiced`
- `test_module_l5_32_package_commission_deadmodel.py::TestLive::test_delete_package_does_not_500`
- `test_module_l5_35_staff_app_jobs_api.py::TestLive::test_field_ops_jobs_list_422s_without_tenant_id_and_succeeds_with_it`
- `test_module_l5_45_package_activation_limits.py::test_activation_creates_and_sets_limits_and_commission_live`
- `test_module_l5_18_invoices.py::TestCustomerInvoices::*` (3 errors)
- `test_p0_navigation_operation_visibility.py::TestEffectiveMenuResolver::*` (2 errors)

None of these touch any file changed this slice. They are reported here, separately, and are
**not** counted toward the passing total.

## Net result

1226 passed / 0 failures attributable to this slice's changes / 11 pre-existing live-environment
exclusions honestly disclosed.
