# Test Quality Report - Slice 2F-31

- Every access-scope claim is read from the LIVE dependency chain via
  `route_guards`, not from a source-string match.
- The "2 routes remain open" claim is asserted as an exact set equality
  against `route-protection-before-after.csv`, with each open route's
  previous/final status asserted identical (no silent partial credit).
- Set B additions are asserted BOTH present in canonical AND unprotected -
  a test that only checked presence could hide a fabricated closure.
- The non-allow-listed router is asserted untouched by content, not by
  omission.
- Coverage arithmetic is asserted against the mission's own formula
  (226+c+h, 259+a), not just against the final numbers.
- Every verifier condition has an executed negative fixture.
