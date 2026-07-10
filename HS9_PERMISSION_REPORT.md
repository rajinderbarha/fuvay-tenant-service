# HS9 — Permission Report

## Status: not investigated this pass

Same as HS8/HS8B — the new endpoints (`/complete`'s deduction side
effect, `/usage-credits/balance`, `/usage-credits/ledger`) gate on
`get_current_user` (tenant-facing) and `require_super_admin`
(admin-facing) respectively, not on granular permissions like
`tenant.usage_credits.ledger.read` or
`admin.usage_credits.adjust`. Whether finer-grained RBAC exists
elsewhere in the platform and could be layered onto these new endpoints
was not investigated this pass.

## Verdict
Permission-aware UI/API: **not verified.** No pass/fail claim.
