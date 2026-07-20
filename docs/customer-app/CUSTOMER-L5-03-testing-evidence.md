# CUSTOMER-L5-03 — Testing Evidence

```
npx jest
Test Suites: 37 passed, 37 total
Tests:       267 passed, 267 total
```

(243 carried over from CUSTOMER-L5-00/01/02, 24 new this sprint.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/home/domain/__tests__/category-schema.test.ts` | 6 | valid category, unsafe icon URL rejection, relative URL acceptance, length caps, negative count rejection, missing-field rejection, mixed-validity list handling |
| `features/home/domain/__tests__/discovery-composer.test.ts` | 5 | mapping, dedup-by-id, stable sort with tie-break, deterministic repeat ordering, 12-item cap |
| `features/home/domain/__tests__/greeting.test.ts` | 3 | day-period boundaries, safe first-name extraction, malformed-name fallback |
| `app/startup/__tests__/startup-route-resolver.test.ts` (extended) | +2 | authenticated default-landing → Home, remote-config override still wins over the auth-based default |

## Not Covered

- No `HomeScreen`/`CategoryCard`/`CategoryGrid` component tests — same
  rationale as every previous sprint (pure logic prioritized; see each
  sprint's own testing-evidence doc).
- No integration test against a real/mocked HTTP server for
  `homeApi.listCategories` — `home-api.ts` is a thin wrapper over
  `apiClient` (already tested in CUSTOMER-L5-00).
- No performance test (large category list render timing, list
  virtualization) — not applicable this sprint since the list is capped at
  12 items by design.
