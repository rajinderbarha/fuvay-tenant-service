# Test Report — Slice 2F-6

## New test file
`tests/test_phase2f6_invoice_payment_provider_authorization.py`
Command: `python -m pytest tests/test_phase2f6_invoice_payment_provider_authorization.py -q`
Result: **39 passed**, 0 failed.

## Slice 2F family regression
Command: `python -m pytest tests/ -q -k "phase2f or 2f5 or 2f6"`
Result: **692 passed**, 9655 deselected, 0 failed.

## Existing invoice/payment domain regression
Command: `python -m pytest tests/ -q -k "invoice or payment or sprint23"`
Result: **225 passed**, 10122 deselected, 0 failed (includes the
pre-existing `test_sprint23_invoice_payment.py` bug-fix test suite —
confirms the new guards do not break MODULE-L5-02's prior fixes).

## Tooling verification
- `PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-module app.engines.invoice_payment.provider_router` → `total_routes: 4`, `unverified_count: 0`, exit 0.
- `PYTHONPATH=. python scripts/workflow_rearchitecture/inventory_mutation_routes.py --verify-overlap app.engines.invoice_payment.provider_router app.engines.invoice_payment.admin_router app.engines.invoice_payment.customer_router` → `overlaps_found: 0`, exit 0.

## Files touched
- `app/engines/invoice_payment/provider_router.py`: 4 endpoints newly
  guarded (import added + 1 `Depends(get_current_user)` →
  `Depends(require_tenant_mutation_permission(P.FIELD_OPS_INVOICE_GEN))`,
  3 `Depends(get_current_user)` → `Depends(require_staff_or_above_mutation)`).
- `tests/test_phase2f6_invoice_payment_provider_authorization.py`: new file.
- `docs/workflow-rearchitecture/phase-02a-slice-02f/mutation-enforcement-matrix.csv`:
  updated in place (this module's row + TOTAL row).
- 17 files under `docs/workflow-rearchitecture/phase-02a-slice-02f6/`: new.

No other production file was modified.
