# Test Report — Slice 2F-25A

## New suite
`tests/test_phase2f25a_legacy_review_residual_closure.py` — **36 passed, 1
skipped**

| Class | Tests | Workstream |
|---|---|---|
| `TestAggregateReadScoped` | 5 | WS2 |
| `TestJobRequestReadScoped` | 4 | WS3 |
| `TestCustomerListScoped` | 4 | WS4 |
| `TestCreateRequestParentOwnership` | 10 | WS5 |
| `TestInternalJobCloseCallerRepaired` | 3 | the 2F-25 regression |
| `TestNoPartialState` | 5 | WS12 |
| `TestCoverageQualification` | 3 (1 skipped pre-docs) | WS10 |
| `TestVerifierIsNotVacuous` | 3 | WS9 |

The skipped test guards against the forbidden application-wide-completeness
label appearing in slice docs; it skips only when the docs directory does not
yet exist, and passes once written.

## Verifier
`scripts/workflow_rearchitecture/verify_legacy_review.py` — 25 checks, all
PASS, **exit 0**.

## Existing suites re-run
`test_phase2f25_*` (49), `test_phase2f24_*`, `test_sprint24_*`,
`test_customer_idor.py`, `test_phase11.py` — **187 passed**.

## Full repository
Run twice under a stable environment — see `regression-report.md` for exact
node-ID comparison across both failures and errors.

## Reporting breakdown

| Category | Count |
|---|---|
| **Failures attributable to this slice** | **0** |
| **Errors attributable to this slice** | **0** |
| Environment | API + PostgreSQL + Redis reachable throughout |

## Self-corrections during authoring
1. An assertion matched `ServiceJob` inside its own docstring saying ServiceJob
   is not used. Fixed by stripping docstrings — in the test **and** the
   verifier.
2. A heredoc escape produced a literal newline inside a string, breaking
   collection. Fixed directly.
