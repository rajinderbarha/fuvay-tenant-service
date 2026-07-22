# Test-Count Correction (WS3)

## The true arithmetic

```
2290   collected phase-2F tests immediately before Slice 2F-31A's changes
  -1   net change in tests/test_phase2f31_n01_media_closure.py:
       3 stale-literal coverage tests (233/262, 29 unprotected, arithmetic
       formula) were collapsed into 2 live-state tests during Slice 2F-31A's
       PRIMARY N01 closure work (not the later cross-slice rebaseline) --
       this happened because the coverage figures those 3 tests asserted
       became stale the moment the 5 residual routes closed, and 2 tests
       were sufficient to cover the same ground the 3 used to.
 +30   new tests in tests/test_phase2f31a_n01_residual_closure.py (WS10
       test matrix)
------
2319   final collected phase-2F test count
```

`2290 - 1 + 30 = 2319`. This matches the currently observed
`pytest tests/test_phase2f*.py --collect-only -q` total exactly.

## What did NOT change the count

- ~15 other test files were rebaselined for the 233→238 / 29→24 coverage
  change. All of them received either pure literal-value edits (zero count
  change) or 1:1 test renames (zero count change) — confirmed by node-ID
  diff, not by assumption. Full list: [test-node-id-reconciliation.csv](test-node-id-reconciliation.csv).
- `verify_*.py` scripts are not pytest-collected files; their edits do not
  affect the collected test count.

## Why "2289" appeared in an earlier session summary

An earlier compacted conversation summary (not this slice's own output)
stated "2289 passed" at one intermediate checkpoint — that was the count
**after** the primary N01 closure edits landed (including the -1 collapse)
but **before** the 30 new WS10 tests were added and before the ~15-file
rebaseline was fully complete, i.e. it captured a transient in-progress
state, not the final baseline. It is not in conflict with the 2290-before
/ 2319-after arithmetic above once the timeline is disambiguated; this
document uses the mission's authoritative 2290 baseline and reconciles
forward from it via real node-ID evidence rather than defending the
intermediate figure.

## True final collection total

**2319**, confirmed live: `python -m pytest tests/test_phase2f*.py
--collect-only -q` → `2319 tests collected`.

No test was changed in this slice (2F-32) merely to make this arithmetic
convenient — all reconciliation here is a read-only accounting of changes
already made in Slice 2F-31A.
