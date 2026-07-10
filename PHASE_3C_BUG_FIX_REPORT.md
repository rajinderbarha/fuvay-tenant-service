# Phase 3C — Bug Fix Report

## Bugs found and fixed

1. **`request_id` never actually reached the UI on any error, on any page,
   app-wide.** `ApiError.request_id` was declared as a top-level field
   (correctly matching the backend's real RFC 7807 shape) but `apiFetch`
   only forwarded `err.context` into `ServiceOSError`, and `useApi`'s error
   handler read `e.context?.request_id` — which was always `undefined`
   because `request_id` was never nested inside `context`. Every page's
   `list.requestId && ...` conditional silently rendered nothing. Fixed by
   adding a `requestId` field to `ServiceOSError`, populating it from
   `err.request_id` in `apiFetch`, and reading `e.requestId` directly in
   `useApi`. This is shared infrastructure — the fix benefits every existing
   page in the admin app, not just the two pricing pages.

2. **`useAction` (used by every create/update/approve/reject/validate button
   in the app) never exposed `errorCode` or `requestId` at all** — only a
   plain `error` message string. This meant no mutation error anywhere in
   the app could show its backend `error_code` or `request_id`, which the
   ticket explicitly requires ("Backend validation errors must show message,
   error_code, request_id"). Fixed by extending `useAction`'s return shape
   with `errorCode`, `requestId`, and `context`, all populated from the same
   `ServiceOSError` fix above.

3. **Bargain rule error-code rename regression risk**: the pre-existing test
   `test_provider_override_enforces_platform_min_max` asserted the old
   `OVERRIDE_BELOW_MIN`/`OVERRIDE_ABOVE_MAX` strings, which would have kept
   passing even after the Phase 3B rename to `OVERRIDE_BELOW_PLATFORM_MIN`/
   `OVERRIDE_ABOVE_PLATFORM_MAX` produced a false negative if anyone reverted
   the rename. Updated in Phase 3B to assert the new strings — re-verified
   still passing in Phase 3C's full suite run.

## Bugs found, not fixed (documented as blockers)

None that block Phase 3C's stated acceptance criteria — see
`PHASE_3C_REMAINING_BLOCKERS.md` for scope-boundary items (missing bulk
import/export, no dedicated Drawer component, no multi-role live 403 test).

## Non-bugs investigated and ruled out

- The ₹900 override validation "inconsistency" (sometimes valid, sometimes
  `DUPLICATE_ACTIVE_OVERRIDE`) is not a bug — it's the new Phase 3B
  duplicate-guard correctly reacting to whether an active override already
  exists for that exact tenant/service pair in the current dataset. Both
  code paths were verified to render correctly in the UI.
