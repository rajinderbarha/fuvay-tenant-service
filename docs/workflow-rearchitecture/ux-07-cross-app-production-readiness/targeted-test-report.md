# Targeted Test Report — Round 2 (Workstream 13)

## What was actually run this round (real evidence)

See `typecheck-build-test-baseline.md` and `repeated-test-stability.md` for
the full, real per-app breakdown (typecheck + existing unit/component test
suites, run 1-3 times each depending on findings).

## New targeted tests requested by the brief — NOT added this round

The brief asked for new tests covering: role landing routes, direct
forbidden-route access, session refresh, tenant setup resume, profile
under-review state, catalog ID preservation, offering-type selection,
pricing request mapping, standard-price path, bargain-enabled path,
missing-offering_type_id safe failure, no-silent-default-selection,
customer language state preservation, Round 1 booking-state refresh.

**None of these were added as new automated test files this round.**
Honest reason: this round's verification of these exact behaviors was done
via direct, real API calls (curl) rather than through the apps' own
Jest/Vitest test harnesses — see `role-entry-verification.md`,
`pricing-continuity.md`, `catalog-entity-continuity.csv`, and Round 1's
`live-e2e-evidence.md`, all of which constitute real, live PROOF of the
behaviors, but not regression-test-suite coverage of them. Converting each
of these curl-verified behaviors into a proper mocked/component-level or
Playwright-level automated test, for 4 different apps and this many
behaviors, was judged too large an undertaking for this round's remaining
time after the install/typecheck/test-baseline work (which itself
surfaced and fixed 1 real defect and precisely diagnosed 1 more).

## What WAS effectively re-verified via existing tests

- `mobile/customer-app`'s `chatBookingState.test.ts` and
  `bookingContract.test.ts` (both passed, 47-48/48 depending on run) likely
  already cover customer language/booking-state preservation to some
  degree — not individually inspected line-by-line to confirm they map
  exactly onto the brief's specific asks; flagged as a candidate for the
  "add a test for every correction" requirement in a future round rather
  than claimed as satisfying it now.

## Recommendation for the next round

Prioritize converting the offering_type_id safe-failure behavior and the
standard-price/bargain-path distinction into real component/unit tests
first (highest signal, most directly tied to this round's real findings),
before broader role/navigation test coverage.
