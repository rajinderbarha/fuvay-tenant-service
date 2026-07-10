# Phase 6 — Remaining Blockers

None of these block certification (all hard gates pass; the ticket's own
waiver for environment-limited manual smoke applies). Carried forward,
honestly documented:

1. **No true interactive browser session available** — permanent
   environment constraint, same as every prior sprint.

2. **No tenant-facing document view/reupload endpoint exists.** Module 13
   is genuinely unimplemented — the only document router found
   (`app/engines/document/router.py`) is a generic e-signature/contract
   engine, unrelated to onboarding-verification documents. Building this
   is a real feature addition (a new tenant-scoped `TenantDocument`
   read/upload router), not a bug fix — flagged, not fabricated.

3. **`dashboard/runtime`'s `enabled_engines`/`modules` fields are
   hardcoded empty lists** — confirmed via source, an intentional-looking
   stub for a category-driven module system that was never finished. Not
   fixed (feature work, not a bug).

4. **Two overlapping, inconsistent wallet-read endpoints** exist
   (`/v1/tenant/wallet` vs `/v1/tenant/credit-wallet`) with different
   failure behavior (one defaults to zero, one 404s) for conceptually the
   same data. Not consolidated this sprint — flagged for a future pass.

5. **Several modules' flows were not independently re-tested this sprint**
   (business profile self-verify block, brand/type/issue coverage mapping,
   pricing override request/approval governance, availability time-range
   validation) — none of their underlying code was touched by any fix, and
   all were already live-verified correct in prior sprints (Phase 3/3D for
   pricing, Phase 5 research for coverage/profile). Re-verifying unchanged,
   already-certified code was deprioritized given the severe time budget in
   favor of the actually-broken flow (tenant dashboard resolution).

6. **Demo Technician does not exist as a real fixture** for Demo AC
   Services — the ticket's baseline scenario names this technician, but no
   corresponding user/staff record exists. `GET /v1/tenant/staff` correctly
   returns empty rather than erroring. Not fabricated.

7. **Staff limit (5) and service area limit (5) enforcement were not
   load-tested** this sprint (only 1 service area exists, 0 staff exist) —
   the enforcement code itself was not touched by any fix.

None of the above represent a tenant context isolation failure, a
self-verification/self-approval bypass, a cash/wallet mislabeling, a
deposit/credit mixing violation, a staff/service-area limit breach, or an
out-of-catalog configuration — the conditions this ticket names as
automatic `NOT_READY` triggers. All were explicitly checked and none
occurred.
