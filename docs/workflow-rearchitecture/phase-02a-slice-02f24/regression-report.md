# Regression Report — Slice 2F-24

## Methodology

Exact node-ID identity comparison for **both failures and errors**, per
Workstream 21. No keyword grepping. The 2F-23 slice closed the error-ID gap by
capturing a `-rE` baseline; this slice is the first able to run the full
two-dimensional comparison the methodology asks for.

Baselines used as comparison input:
- failing node IDs — `/tmp/after_full_2f23.txt` (86)
- error node IDs — `/tmp/errors_2f23.txt` (111)

Post-slice capture: `pytest tests/ -q --tb=no -rEf` (both dimensions in one run).

## Headline numbers

| | BEFORE (2F-23) | AFTER (2F-24) | Δ |
|---|---|---|---|
| passed | 11146 | **11192** | +46 |
| failed | 86 | **86** | 0 |
| errors | 111 | **111** | 0 |
| skipped | 14 | **14** | 0 |

## Failing node IDs

```
comm -13 <before> <after>  ->  (empty)   # new failing:  ZERO
comm -23 <before> <after>  ->  (empty)   # resolved:     ZERO
```
**86 unchanged, byte-identical.**

## Error node IDs

```
comm -13 <before> <after>  ->  (empty)   # new errors:      ZERO
comm -23 <before> <after>  ->  (empty)   # resolved errors: ZERO
unchanged: 111
```
**111 unchanged, byte-identical.**

## Passed delta reconciles exactly

+46 = the 46 tests in
`tests/test_phase2f24_customer_review_authorization.py`. Nothing else moved.

Note this is a *net* figure that happens to be clean: several pre-existing
tests were touched this slice (3 mock doubles in
`test_sprint24_customer_reviews.py`, plus assertions in the 2F-21 and 2F-23
suites). All continued to pass, so they neither add nor remove from the count.

## Tests deliberately modified, and why

Reported explicitly rather than absorbed into the delta:

| File | Change | Rationale |
|---|---|---|
| `test_sprint24_customer_reviews.py` | 3 mock doubles re-pointed from `_get_review` to `_get_review_scoped`; one call given a scope | The refactor renamed the internal helper the doubles patched. Intent of each test unchanged. |
| `test_phase2f21_...selection.py` | live-canonical sum 207→209; 2 reviews routes added to the named `PROTECTED_BY_LATER_SLICE` exemption | 2F-21's own CSV left untouched — it is a truthful point-in-time record |
| `test_phase2f23_...selection.py` | reverification exemption; **defect assertions INVERTED**; indirect-audit token list scoped; no-app-change assertion re-pointed | 2F-23 deliberately asserted the defect against live source so it could not rot. 2F-24 closed it, so each assertion now fails if the fix is **reverted** — the guard is preserved, not deleted |
| `test_phase2f14a`, `test_phase2f17a`, `test_phase2f19` | recount 207→209, remainder 19→17 | live-canonical assertions |

The 2F-23 inversion is the notable one: those five tests existed precisely to
detect this change, and they fired. Rather than deleting them, each now
asserts the fixed state, so the protection they provide continues in the
opposite direction.

## Classification

- **Attributable to Slice 2F-24: 0 failures, 0 errors.**
- Pre-existing unrelated: 86 failures, 111 errors — dominated by
  `httpx.ConnectError` / `ConnectionRefusedError` live-environment
  dependencies.
- Live-environment exclusions: all DB- and HTTP-backed tests. No claim in this
  slice depends on one.
- **Slice-2D canaries:** still failing, still untouched, within the unchanged 86.

## Statement

Zero regressions — supported by exact before/after node-ID identity comparison
across **both** failures and errors, which is the first time in this
initiative that both dimensions have been compared at ID level.
