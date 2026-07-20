# Regression Report — Slice 2F-23

## Methodology

Exact failing-node-ID identity comparison, per Workstream 12. Keyword
grepping is not used to infer attribution — that method is what allowed
Slice 2F-20 to ship a regression while reporting "zero regressions".

Comparison input: the Slice 2F-22 baseline (11108 passed / 86 failed / 111
errors / 14 skipped), treated as data to diff against, not as an assumption
that every failure is unrelated.

## Headline numbers

| | BEFORE (2F-22) | AFTER (2F-23) | Δ |
|---|---|---|---|
| passed | 11108 | **11146** | +38 |
| failed | 86 | **86** | 0 |
| errors | 111 | **111** | 0 |
| skipped | 14 | **14** | 0 |
| duration | 652.97s | 673.80s | — |

## Failing node IDs — exact comparison

```
comm -13 <before> <after>   ->   (empty)    # new failing:  ZERO
comm -23 <before> <after>   ->   (empty)    # resolved:     ZERO
```

**86 unchanged pre-existing failures, byte-identical node IDs.**

## Passed delta reconciles exactly

+38 = the 38 tests in
`tests/test_phase2f23_remaining_queue_reconciliation_and_selection.py`.
Nothing else moved in either direction.

## Error node IDs

111 error node IDs were captured this slice with `-rE` and are enumerated in
full. By file:

| Count | File |
|---|---|
| 23 | `test_p0_provider_enterprise.py` |
| 21 | `test_trust_quality_phase1.py` |
| 19 | `test_p0_service_options_enterprise.py` |
| 18 | `test_p0_notification_template_center.py` |
| 9 | `test_module_l5_12_trust_quality.py` |
| 5 | `test_p0_navigation_operation_visibility.py` |
| 5 | `test_module_l5_15_privacy.py` |
| 3 | `test_p0_sidebar_duplicate_cleanup.py` |
| 3 | `test_module_l5_18_invoices.py` |
| 3 | `test_module_l5_17_credits.py` |
| 1 | `test_module_l5_47_dispatch_notify.py` |
| 1 | `test_module_l5_13_reviews.py` |

### Methodology limitation, stated rather than glossed

**Per-ID before/after comparison of errors was not possible**, because the
2F-22 baseline run captured failures only (`-rf`), so no error-ID list exists
for the "before" side. What is established is:

- error **count** parity: 111 → 111;
- every one of the 111 lies in a file unrelated to this slice;
- **zero files under `app/` were modified**, so no error can be attributable
  by construction.

The `-rE` capture made here becomes the baseline error-ID list for the next
slice, so this gap closes going forward. It is recorded as a limitation
rather than presented as an ID-level comparison that was not performed.

### The one reviews-related error was checked specifically

`test_module_l5_13_reviews.py::TestBookingRatingEndToEnd::test_rating_lands_in_customer_reviews_and_provider_sees_it`
was executed in isolation because it touches the module this slice selected.
Cause: `httpx.ConnectError: All connection attempts failed` — a live-server
dependency. The remaining 2 tests in that file pass. Not attributable.

## Classification

- **Attributable to Slice 2F-23: 0 failures, 0 errors.**
- Pre-existing unrelated: 86 failures, 111 errors — dominated by
  `httpx.ConnectError` / `ConnectionRefusedError` live-environment
  dependencies.
- Live-environment exclusions: all DB- and HTTP-backed tests. No claim in
  this slice depends on one.
- **Slice-2D canaries:** still failing, still deliberately untouched, counted
  within the unchanged 86.

## Statement

Zero regressions, supported by exact failing-node-ID comparison for failures
and by count parity plus a zero-`app/`-change argument for errors — with the
error-ID methodology gap disclosed rather than papered over.
