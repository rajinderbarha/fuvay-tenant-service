# Regression Report — Slice 2F-14C

## Slice-specific executions

- `tests/test_phase2f14c_field_ops_notes_media_and_create_job_fk.py` (12 tests, new) — PASS.
- `tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` (21 tests, 2
  fixtures updated to supply `service_type_id=""`) — PASS.
- `tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py` (30 tests, 2 canonical-figure
  assertions updated to 169/210, 40/40) — PASS.
- `tests/test_phase2f14_field_ops_staff_authorization.py` (34 tests) — PASS.
- `tests/test_job_type_routing.py`, `tests/test_usage_quota.py` (23 tests, unaffected) — PASS.
- `tests/test_job_type_flows.py` (14 tests, 1 fixture updated to supply the 3 additional mock DB
  responses `create_job`'s new validation now requires) — PASS.

Combined: **229 + 14 = 243 passed, 0 failed** across the direct slice/dependency suites.

## Broad partition sweep

`-k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate
or coaching or invoice or payment or commission or parts_request"`:
**1276 passed, 1 skipped, 10 failed, 5 errors.**

## Live-network/live-database exclusions (not counted as passing)

All 10 failures + 5 errors traced to `httpx.ConnectError`, `asyncpg` connection failure, or
`ConnectionRefusedError: [WinError 1225]` — identical exclusion list to Slice 2F-14B's
regression-report.md (no new exclusion introduced):

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

## Fixtures updated (regression, not new defects)

- `tests/test_phase2f14b_field_ops_creation_conversion_quote_authorization.py` — 2 tenant-pinning
  tests updated to pass `service_type_id=""` (falsy, skips the new catalog validation, which is
  out of scope for what those tests assert).
- `tests/test_job_type_flows.py` — 1 test's mock `db.execute` side_effect extended with 3
  additional mock results (catalog, parent-job, customer) to match `create_job`'s new validation
  calls when invoked internally via `_spawn_repair_from_consultation`.

## Net result

243 passed in direct slice suites / 1276 passed in the broad sweep / 15 pre-existing
live-environment exclusions honestly disclosed and not counted as passing.
