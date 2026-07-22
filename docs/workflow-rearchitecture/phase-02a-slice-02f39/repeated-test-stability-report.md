# Repeated Test Stability Report

- Phase-2F suite: run twice, identical (2473/2473 both times, see
  `phase2f-regression-report.md`).
- Full backend suite: run once (1356.99s / 22:36 — a second run was not
  performed this slice given the cost; see `known-limitations.md`).
- Targeted stability proof for the specific test-order issue found: the
  polluting test (`test_dispatch_job_sync.py`) run immediately before the
  previously-polluted test
  (`test_phase2f35_critical_authorization_batch.py::TestDocumentTenantAuthority`)
  in the same invocation — all pass, confirmed via `-v` output naming
  each test individually.
