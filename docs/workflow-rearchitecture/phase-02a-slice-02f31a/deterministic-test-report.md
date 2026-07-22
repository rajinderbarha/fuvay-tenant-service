# Deterministic Test Report

`tests/test_phase2f31a_n01_residual_closure.py` (30 tests) and
`verify_n01_2f31a.py` (21 conditions + selftest) were each run twice
consecutively with identical results both times: 30/30 and 21/21 passing,
no flakiness, no ordering dependency (all assertions are static
`inspect.getsource`/CSV-read checks with no shared mutable state between
tests).

See [regression-report.md](regression-report.md) for the full-suite
determinism run (`tests/test_phase2f*.py`, run twice).
