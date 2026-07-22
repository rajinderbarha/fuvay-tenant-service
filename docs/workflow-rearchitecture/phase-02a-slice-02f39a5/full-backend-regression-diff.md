# Full Backend Regression Diff — Slice 2F-39A5

## Result

`python -m pytest tests/ -q`: **11,976 passed, 57 failed, 33 skipped,
111 errors** (12,177 total accounted for), 865.68s (0:14:25).

## Identical failure set to Slice 2F-39A4 — confirmed byte-for-byte

The 57 `FAILED` lines in this run are **byte-for-byte identical** to
Slice 2F-39A4's full-suite run (`diff` shows zero differences). This
includes:
- The 26 known baseline failures (unchanged since Slice 2F-39A).
- The 31 `LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED` failures + 111
  errors (per the Slice 2F-39A4 review's disposition label) — all
  `httpcore.ConnectTimeout` inside `TestLive`-suffixed tests or
  `test_no_auth_returns_4xx`-style live-endpoint checks, unrelated to
  any authorization logic.

**No failure anywhere in this run names or asserts on
`route_operation`, `hold_slot`, `ingest_event`, `send_notification`, or
`retry`** (confirmed via direct grep of the failure list for these
route/function names — zero matches).

## Disposition

Carries forward `LIVE_TEST_INFRASTRUCTURE_CAPACITY_BLOCKED` unchanged
from Slice 2F-39A4, still pending Slice 2F-39C's controlled-capacity
reproduction. The fact that this failure set reproduced identically
across two independent full-suite runs (different slices, different
code changes, ~70 seconds apart in duration) is itself useful evidence
for that future investigation — it points toward a fixed capacity
ceiling or a deterministic resource-exhaustion point in the test run
order, rather than random flakiness.

This slice's own 7 targeted tests and both Phase-2F full runs
(2526/2526, twice) remain the authoritative evidence that the 5 fixes
themselves are correct and introduce no regression.
