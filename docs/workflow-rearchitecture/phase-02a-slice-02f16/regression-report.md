# Regression Report

## New tests
`tests/test_phase2f16_quote_checklist_authorization.py` — 21/21 passing:
- Router-guard source proofs (2)
- `get_quote`/`get_checklist` IDOR fix (4, including privacy field-stripping — 2 more added mid-slice)
- `create_checklist` job-ownership fix (3)
- Amount-integrity negative-value rejection (3)
- Post-final/post-send item-mutation lock (3)
- Customer decision ownership, re-verified (2)
- Invoice-from-quote cross-tenant/status bypass fix (2)
- Privacy field-stripping (2)

## Existing tests fixed
`tests/test_sprint22_quote_checklist.py::TestChecklists::test_create_checklist_no_template` — required an additional mocked `db.execute` result (the new job-lookup query added by this slice's `create_checklist` ownership fix) — additive mock scaffolding only, no behavioral logic changed.

## Canonical coverage test updated
`tests/test_phase2f14a_field_ops_alternate_route_and_coverage.py::TestCanonicalCoverageRecount::test_canonical_totals` — updated from `216/175` (2F-15C) to `227/186` (this slice), reflecting the 11 newly-protected quote_checklist tenant/provider mutation rows.

## Suite executions (all overlapping, no live-environment exclusions)
| Suite | Result |
|---|---|
| `test_phase2f16_quote_checklist_authorization.py` (new) | 21 passed |
| `test_sprint22_quote_checklist.py` (existing quote_checklist tests, 1 fixed) | 50 passed |
| `test_sprint23_invoice_payment.py` (existing invoice/payment/commission tests) | 176 passed, 1 skipped |
| `test_phase2f14a_field_ops_alternate_route_and_coverage.py` (coverage recount, updated) | 30 passed |
| Existing field_ops quote tests (part of `field_ops.router`'s own suite) | included in full sweep, unchanged |
| Existing Booking tests (2F-15/15A/15B/15C series) | included in full sweep, unchanged |
| Existing ServiceJob-relevant tests | included in full sweep, unchanged |
| Existing PartsRequest tests | included in full sweep, unchanged (no reference from quote_checklist) |
| `field_ops.router`/`field_ops.staff_router` runtime verification | exit 0, unchanged |
| Coverage recount verification | `test_canonical_totals` updated, passing |

## Full broad partition sweep
```
python -m pytest -q -k "field_ops or checklist or step8 or step7 or job_type or quote or complaints or real_estate or coaching or invoice or payment or commission or parts_request or booking"
1753 passed, 9 skipped, 9288 deselected, 49 warnings
```
Zero failures (up from 1734 at the 2F-15C gate: +19 net new passing, some counted in different `-k` partitions across the two runs performed this slice).

## Live-environment exclusions
No live server/database verification was performed this slice — unit tests (mocked `AsyncSession`) plus executed runtime route-introspection only, consistent with every prior slice in this initiative.

A later, wider `-k` sweep in this same session surfaced 15 additional failures/errors (`test_module_l5_16_quotes.py`, `test_module_l5_18_invoices.py`, `test_module_l5_21_quote_notify.py`, `test_module_l5_26_invoice_notify.py`, `test_module_l5_27_booking_notify.py`, `test_module_l5_28_credit_checkout.py`, `test_module_l5_29_booking_cancel_reschedule.py`, `test_module_l5_32_package_commission_deadmodel.py`, `test_module_l5_35_staff_app_jobs_api.py`, `test_module_l5_45_package_activation_limits.py`, `test_module_l5_13_reviews.py`, `test_p0_navigation_operation_visibility.py`, `test_final_l5_04c_matching_entitlement.py`). All 15 are confirmed **live-environment tests** — they connect to `http://localhost:8000` via `httpx.AsyncClient` and/or open a real `asyncpg` connection to a Postgres database (test class names literally contain `Live`, e.g. `TestQuoteNotifyLive`, `TestCancelRescheduleLive`). Direct reproduction of one failure shows `ConnectionRefusedError: [WinError 1225] The remote computer refused the network connection` — no live server or database was running in this session's environment. `curl http://localhost:8000/health` independently confirms no server is listening. These are **environmental exclusions, not regressions**: none of them exercise mocked/unit-level code paths this slice touched, and none were part of the 1753-passed mocked-unit sweep reported above. Reported here separately, honestly, per this slice's explicit instruction not to count live-environment exclusions as passing.
