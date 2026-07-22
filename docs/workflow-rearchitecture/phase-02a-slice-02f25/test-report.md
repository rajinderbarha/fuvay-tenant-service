# Test Report — Slice 2F-25

## New suite
`tests/test_phase2f25_legacy_review_engine_authorization.py` — **49 passed**

| Class | Tests | Workstream |
|---|---|---|
| `TestModelDistinctness` | 3 | WS2 |
| `TestScopedLookup` | 5 | WS5 |
| `TestEffectiveTenant` | 8 (incl. 5 parametrised method checks) | WS8 |
| `TestMutationAuthority` | 8 | WS6 |
| `TestReadPrivacy` | 3 | WS7 |
| `TestLegacy410Preserved` | 3 | WS12 |
| `TestFrontendCallerInventory` | 4 | WS11 |
| `TestCanonicalCoverage` | 6 | WS17 |
| `TestPreviousClosuresIntact` | 3 | preservation |

Notable assertions:
- `db.execute.assert_not_called()` for a tenantless principal — the guard
  fires before any query.
- WHERE-clause inspection rather than whole-statement matching (see
  `documentation-corrections.md` #4).
- A caller inventory listing all six applications, failing if one disappears.

## Existing suites re-run
`test_customer_idor.py`, `test_phase11.py`, `test_module_l5_13_reviews.py`,
`test_sprint24_customer_reviews.py`,
`test_phase2f24_customer_review_authorization.py` — **140 passed**, 1
pre-existing live-environment error.

Recount suites (`test_phase2f14a`, `2f17a`, `2f19`, `2f21`, `2f23`, `2f24`) —
**162 passed** after the 229/212 update.

## Reporting breakdown

| Category | Count |
|---|---|
| **Failures attributable to this slice** | **0** |
| **Errors attributable to this slice** | **0** |
| Live-environment exclusions | all DB/HTTP-backed tests |

Full-repository figures and the exact node-ID comparison are in
`regression-report.md`.

## Environment exclusions
No database or live HTTP server. Every new test is deterministic. The
cross-tenant fixes are proven by SQL-predicate presence and by denial paths
writing nothing — not claimed as live end-to-end verification.
