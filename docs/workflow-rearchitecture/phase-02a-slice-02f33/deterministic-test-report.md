# Deterministic Test Report

`tests/test_phase2f33_geo_zone_closure.py` (25 tests) and
`verify_geo_2f33.py` (22 conditions + selftest) were each run multiple
times with identical results: 25/25 and 22/22 passing, no flakiness, no
ordering dependency (all assertions are static `inspect.getsource`/CSV-
read/live-route-introspection checks with no shared mutable state between
tests).

See [regression-report.md](regression-report.md) for the full-suite
determinism run (`tests/test_phase2f*.py`, run twice).
