# Slice 2F-39A — Implementation Summary

## Final status: `AUTHORIZATION_REMEDIATION_BLOCKED`

This slice resumed from Slice 2F-39's baseline (`26b0109`) to work
specifically on the two items 2F-39 left open: the incomplete
mounted-route census (261 unresolved) and the two
`test_sprint27_notifications.py` failures flagged as possibly
authorization-adjacent.

## What was achieved

1. **Notification chat-access investigation — fully resolved.** Both
   failures traced to a stale expected error-message string, not an
   authorization defect: `ChatThreadService.validate_thread_access` was
   deliberately upgraded (by an earlier slice) to a non-oracular
   `ERR_CHAT_THREAD_NOT_FOUND` for both "thread doesn't exist" and
   "thread exists but isn't yours," matching this program's established
   Booking-series privacy pattern. Access was and remains correctly
   denied in both cases. Both tests fixed; all 44 tests in that file now
   pass.
2. **8 newly discovered canonical tenant/provider mutations added** to
   the inventory, found by reading `app/engines/auth/router.py`'s actual
   guard dependencies rather than trusting the auto-classifier's
   `UNVERIFIED` label: `create_api_key`, `revoke_api_key`,
   `update_api_key` (each with a dedicated new test proving real
   tenant-scoping), plus `invite_staff`, `update_permissions`,
   `deactivate_staff`, `resend_invite`, `update_staff_schedule` (verified
   by guard-pattern reading only). Honest denominator: **313 → 321**.
3. **One full module (32 routes) classified end-to-end** with real
   source evidence: 8 canonical, 2 platform-admin, 9 public/callback, 13
   self-service (broadened, documented rationale in
   `route-classification-contract.md`).

## What remains open

**229 of the original 261 unresolved routes remain genuinely
unclassified**, spanning 32 other modules. This is 12% complete by route
count — an honest, quantified partial result, not a stalled or hidden
one. See `known-limitations.md` and `deferred-items.md` for the exact
remaining scope and a prioritized completion order.

## Evidence

- Phase-2F regression: 2477/2477 passed, twice, identical (2473 baseline
  + 4 new tests).
- Full backend regression: see `full-backend-regression-diff.md`.
- `verify_2f37.py`: 21/21 PASS, reconfirmed, unaffected by this slice's
  test-only changes.
- Zero application-code files changed — only 2 test files
  (`test_phase2f39a_canonical_additions.py` new,
  `test_sprint27_notifications.py` modified).

This slice stops at its own approval gate. Slice 2F-39B/2F-40 are not
started; demo-account decisions, Migration 144 execution, and final
application-wide certification remain out of scope for this slice.
