# Documentation Corrections — Slice 2F-26

## 1. The 229 denominator was incomplete — corrected to 257

Not wrong by counting: complete only within the prefix convention it was built
on. 28 tenant mutations on generic prefixes had no canonical row. This is the
same class of finding as 2F-25's `/v1/reviews` discovery, at eight times the
scale.

## 2. "1186 mounted mutation routes" understates the surface

The pre-existing tool filters to POST/PUT/PATCH/DELETE **before** inspecting
behaviour, so it cannot see mutating GETs. The true mounted surface is 2299
routes, of which 1058 are genuine mutations by side effect — a set that
differs from the 1186 method-based set in **both** directions (31 mutating
GETs in; 145 read-only POST/PUT/PATCH out).

## 3. `test_phase2f17a`'s runtime-match assertion was method-limited

`test_every_canonical_row_is_mounted_at_runtime` used the mutation-only walker
and therefore could not see the two new mutating-GET rows. Widened with a
GET-inclusive walk rather than exempting those rows — the point is to prove
they are mounted.

## 4. Four of my own tooling bugs, and one classifier error

Recorded in full in `implementation-summary.md`. Two are worth repeating
because they would have produced confidently wrong output:

- The first sweep returned an **empty** route list (FastAPI wrapper nesting).
  Published as-is it would have read as "no routes found".
- The first persona rule disagreed with **149 of 229** canonical rows. I
  treated that as evidence against my classifier, not against the CSV, and
  replaced the rule.

## 5. A contaminated baseline measurement — my error

I launched the pre-slice baseline in the background and then modified the
canonical CSV while it ran, invalidating it (13 spurious recount failures).
Discarded; 2F-25A run 2 used instead. Full account in
`environment-test-evidence.md`.

## 6. I was wrong about a route my tooling flagged

I suspected `GET /v1/commerce/.../deposit` was a false positive. It is not:
`get_deposit_status()` calls `_get_or_create_deposit()` and lazily creates a
row. The tool was right; my intuition was wrong. Recorded because the
temptation was to "clean up" a result that looked odd.

## 7. Forward annotation added to Slice 2F-25A
