# Regression Report - Slice 2F-29

## Before (pre-slice baseline, excludes this slice's new M01 test file)
Full phase-2F suite green: 2170 passed, 0 failed, 0 errors.

## After the code change (pre-rebaseline)
42 failures, all attributable to the intended canonical movement
(214 -> 226, 45 -> 33, new canonical/matrix hashes) plus **one behavioural
test** pinning the removed oracle.

## Resolution
- ~25 current recount/hash assertions rebaselined to the new live values.
- Two 2F-28 assertions that count its **historical** 45-route queue artifact
  were restored to 45 after an over-broad substitution, and the live-comparing
  assertions were reframed as `live_unprotected + closed_M01 == queue`.
- `test_cross_tenant_target_still_rejected` updated to assert `NOT_FOUND` and
  the absence of the tenant-membership phrase.

## Final
- **2213 passed, 0 failed, 0 errors** (this total already includes the 43 new
  M01 tests; the pre-slice baseline was 2170).
- New failures: none. Resolved failures: 42 (all intended). Unchanged
  failures: none. New errors: none.
- Canonical hash `fbe7cf863afa0d84`; matrix hash `753653ed32916f4e`.
- Changed application files: `app/engines/auth/router.py`,
  `app/engines/auth/service.py`.
