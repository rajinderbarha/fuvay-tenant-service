# HS8B — Permission UI Report

## Status: not investigated this pass

Same as HS8's own permission report — the endpoints exercised this pass
(parts request create/approve/reject/install, completion) gate on
`get_current_user` (any authenticated user of the right role reaches the
handler), not on granular RBAC permissions
(`tenant.jobs.parts.approve`, `staff.jobs.complete`, etc.). Whether more
granular permission infrastructure exists elsewhere in the platform and
is simply not wired into these specific new endpoints was not
determined this pass — genuinely not investigated, not confirmed absent.

## Verdict
Permission-aware UI: **not verified.** No pass/fail claim.
