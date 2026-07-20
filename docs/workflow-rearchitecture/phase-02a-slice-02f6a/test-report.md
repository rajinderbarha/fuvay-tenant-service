# Test Report — Slice 2F-6A

## New test file
`tests/test_phase2f6a_invoice_payment_integrity.py`
Command: `python -m pytest tests/test_phase2f6a_invoice_payment_integrity.py -q`
Result: **29 passed**, 0 failed.

## Updated existing test file
`tests/test_phase2f6_invoice_payment_provider_authorization.py` — updated
to reflect the technician-narrowing decision (technician moved from
authorized to denied for the 3 `require_owner_or_office_staff_mutation`
routes).
Command: `python -m pytest tests/test_phase2f6_invoice_payment_provider_authorization.py -q`
Result: **39 passed**, 0 failed.

## Pre-existing regression tests updated (honest fix, not a workaround)
Two pre-existing "living count" guardrail tests failed after this
slice's changes and were updated to reflect documented, intentional
growth (both explicitly say "if this changed, update the count" in
their own docstrings):
- `tests/test_phase2d_tenant_access_model.py::TestTenantMutationPermissionCoverage::test_coverage_of_require_tenant_mutation_permission_is_still_narrow`
  — count updated from 3 to 4 (Slice 2F-6 added
  `invoice_payment/provider_router.py` as a 4th user of
  `require_tenant_mutation_permission`).
- `tests/test_phase2e_effective_permissions.py::TestMutationGuardCoverageSurvey::test_only_one_router_file_uses_require_tenant_mutation_permission`
  — expected list updated to include
  `app/engines/invoice_payment/provider_router.py`.
Command: `python -m pytest tests/test_phase2d_tenant_access_model.py tests/test_phase2e_effective_permissions.py -q`
Result: **27 passed**, 0 failed (after the update).

## Combined targeted regression
Command: `python -m pytest tests/ -q -k "phase2f or 2f5 or 2f6 or invoice or payment or sprint23"`
Result: **902 passed**, 0 failed.

## Broader partition (ServiceJob/permission/access-scope)
Command: `python -m pytest tests/ -q -k "servicejob or service_job or access_scope or permission or phase2f or 2f5 or 2f6 or invoice or payment or sprint23"`
Result: **1165 passed**, 0 failed.

## Tooling verification
- `PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.invoice_payment.provider_router` → `total_routes: 4`, `unverified_count: 0`, exit 0.
- `PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-overlap app.engines.invoice_payment.provider_router app.engines.invoice_payment.admin_router app.engines.invoice_payment.customer_router` → `overlaps_found: 0`, exit 0.

## Files touched
- `app/engines/invoice_payment/payment_service.py` — amount + invoice-state validation added to `record_onsite_payment`.
- `app/engines/invoice_payment/invoice_service.py` — quantity/unit_price validation added to `add_item`.
- `app/engines/invoice_payment/provider_router.py` — technician-excluding guard applied to 3 routes; ValueError→4xx mapping added to `provider_issue_invoice`/`staff_create_invoice`/`staff_add_invoice_item`.
- `app/core/permissions.py` — new `require_owner_or_office_staff_mutation` composed dependency.
- `scripts/workflow_rearchitecture/inventory_mutation_routes.py` — `guard_status()` extended to recognize the new dependency.
- `tests/test_phase2f6a_invoice_payment_integrity.py` — new.
- `tests/test_phase2f6_invoice_payment_provider_authorization.py` — updated (technician role-set correction).
- `tests/test_phase2d_tenant_access_model.py`, `tests/test_phase2e_effective_permissions.py` — updated (documented-growth count corrections).
- 15 files under `docs/workflow-rearchitecture/phase-02a-slice-02f6a/`: new.

No other production or test file was modified.
