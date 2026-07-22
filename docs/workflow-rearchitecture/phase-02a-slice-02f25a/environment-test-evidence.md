# Environment and Test Evidence — Slice 2F-25A

## The contradiction being corrected

Slice 2F-25's artifacts contained both:

- `known-limitations.md`: "**No live database or HTTP server.** All 49 new
  tests are deterministic..." ; and
- `regression-report.md`: "The API server, PostgreSQL and Redis became
  **reachable** ... 79 failures and all 111 errors resolved environmentally."

Both statements were written during the same slice. The first was inherited
boilerplate from earlier slices and was **stale by the time the slice closed**;
the second was the freshly measured truth. The stale one should have been
retracted, not left standing beside its own contradiction.

## Measured state — Slice 2F-25A

Direct socket probe at slice start (2026-07-18T23:40:18):

| Service | Port | State |
|---|---|---|
| API server | 8000 | **REACHABLE** |
| PostgreSQL | 5432 | **REACHABLE** |
| Redis | 6379 | **REACHABLE** |

## Which test groups used what

| Group | Postgres | Redis | API server | Mocked |
|---|---|---|---|---|
| `test_phase2f25a_*` (this slice, 36) | no | patched | no | **yes — session doubles** |
| `test_phase2f25_*` (49) | no | patched | no | yes |
| `test_phase2f24_*`, `test_sprint24_*` | no | no | no | yes |
| `test_module_l5_13_reviews.py::TestBookingRatingEndToEnd` | **yes** | yes | **yes** | no |
| `test_customer_idor.py`, `test_phase11.py` | some | some | some (TestClient) | mixed |
| `test_final_l5_*`, `test_p0_*`, `test_trust_quality_*` | **yes** | yes | mixed | no |

## What remains genuinely unavailable

Nothing was skipped for want of infrastructure in the final run. The residual
limitation is different in kind: **this slice's own 36 tests are deliberately
deterministic** (session doubles, source introspection) rather than live
integration tests. That is a design choice for speed and determinism, not an
environment constraint — and it is why the security claims rest on SQL-
predicate inspection plus no-write assertions rather than on executed
cross-tenant requests.

An executed-exploit test against the live database would be stronger evidence.
It is recorded as a deferred item, not claimed.

## Availability at slice completion

Re-probed after the final test runs: all three services still reachable. The
environment was stable across both runs, satisfying the mission's requirement
to run the final partition twice under the same conditions.

## Attribution rule applied

No environment-resolved test is attributed to an application change. See
`regression-report.md` for the exact node-ID comparison.
