# CUSTOMER-L5-04 — Test Evidence

```
npx jest
Test Suites: 56 passed, 56 total
Tests:       370 passed, 370 total
```

(312 carried over from CUSTOMER-L5-00 through the deepened CUSTOMER-L5-03
pass, 58 new this sprint.)

## New Test Files

| File | Count | Covers |
|---|---|---|
| `features/category/domain/__tests__/category-detail-schema.test.ts` | 6 | valid payload, missing field, unsafe image URL rejected, relative image URL accepted, malformed payload doesn't throw |
| `features/category/domain/__tests__/offering-schema.test.ts` | 7 | list page parse, per-item drop-not-fail, malformed envelope, detail parse, missing `required_fields`, `is_available: false` still parses |
| `features/category/queries/__tests__/category-query-keys.test.ts` | 5 | detail/offerings key scoping by category, locale, tenant |
| `features/category/components/__tests__/ServiceListItem.test.tsx` | 2 | renders name, fires onPress with the offering, hides price line when zero |
| `features/service-detail/domain/__tests__/booking-boundary.test.ts` | 4 | all 4 (auth × devBuild) combinations, fails closed |
| `features/service-detail/queries/__tests__/service-detail-query-keys.test.ts` | 4 | scoping by category, service, locale, tenant |
| `features/search/domain/__tests__/query-normalization.test.ts` | 11 | trim, whitespace collapse, control-char strip, Unicode (Hindi/Punjabi) preservation, max length, min-length gate, buckets |
| `features/search/domain/__tests__/search-schema.test.ts` | 5 | both result types, per-item drop-not-fail (both types), malformed envelope, empty results |
| `features/search/queries/__tests__/search-query-keys.test.ts` | 4 | query/category/locale scoping |
| `features/search/state/__tests__/recent-search-storage.test.ts` | 8 | empty start, add-to-front, dedupe-on-research, 10-item cap, remove, clear, cross-customer isolation, clear-one-doesn't-affect-other |
| `navigation/deep-links/__tests__/deep-link-validator.test.ts` (extended) | +5 | category deep link, service deep link (both segments), missing-category-segment rejected, malformed category id rejected, search deep link |

## Regression Confirmation

All 312 tests from before this sprint continue passing unmodified,
including every `auth`/`home`/`remote-config`/`deep-link`/`route-guards`
suite — confirming the route-registry changes (`serviceDetails`/`search`
access-policy promotion) and the `home-api.ts` dead-code removal introduced
no regressions.

## Not Covered This Pass

- No component/render tests for `CategoryDetailScreen`, `ServiceDetailScreen`,
  or `SearchScreen` themselves — consistent with every previous sprint's
  identical, explicitly-stated deprioritization of screen-level render tests
  in favor of pure-logic + one-level-up component coverage (`ServiceListItem`
  is the one exception added this pass, matching the project's existing
  `AppButton`/`AppCard` component-test precedent).
- No `useDebouncedValue`/`useRecentSearches` hook-render tests — these are
  thin wrappers over already-unit-tested pure functions
  (`normalizeSearchQuery`, `recent-search-storage.ts`) plus React state; no
  prior sprint in this app has written a `renderHook`-based test either (none
  exists in the repository), so this keeps the established pattern rather
  than introducing a new testing style unilaterally.
- No true integration test mocking only the HTTP boundary across the full
  Home → Category → Service → Booking-boundary chain in one test.
- No live runtime proof — see `CUSTOMER-L5-04-runtime-evidence.md`.
- No multi-tenant isolation test with real data (single-tenant sandbox).
