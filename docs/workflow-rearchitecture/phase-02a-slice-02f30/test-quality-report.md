# Test Quality Report - Slice 2F-30

- The queue is verified by **set equality against the live canonical file**, so
  canonical drift fails the suite.
- M01 non-regression is asserted two ways: absent from the queue **and** all 12
  still in the protected set.
- Set B non-emptiness is asserted (3 routes) together with the assertion that
  none of them is canonical - the opposite of M01, where emptiness was proven.
- Frozen Set A/B/C hashes are asserted, so a silent scope change breaks tests.
- The contract is machine-checked to contain every Set A route and to smuggle
  no Set C route.
- The selection is asserted to be top-ranked **and** the risk file is asserted
  to carry the ownership-evidence column, so a score without evidence fails.
- Every verifier condition has an executed negative fixture.
