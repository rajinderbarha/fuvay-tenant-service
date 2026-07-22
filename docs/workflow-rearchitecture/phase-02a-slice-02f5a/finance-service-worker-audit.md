# Service and Worker Caller Audit — Workstream 10

## package_commerce.admin_router
- `PackageCommerceService.create_package_assignment` — 2 registered API
  callers found (`admin_purchase_package`, `tenant_purchase_package`), no
  worker or scheduled-job caller found.
- `UsageCreditService` (reached via `admin_topup_wallet`/`admin_adjust_wallet`)
  — not independently re-audited for its own full caller list this slice
  (out of narrow scope; it is an existing, previously-audited canonical
  service per FINAL-L5-05J).
- Commission calculation/deduction service internals — not traced this
  slice.

## finance_hub.admin_router
- Shared `_svc`/`require_finance_hub_read` dependency pattern — every
  mutation endpoint also depends on `require_finance_hub_read` (visible in
  the dependency list for all 17 routes), suggesting a base "can view
  finance hub" gate layered under the specific permission gate. Not traced
  to its exact implementation this slice.
- No worker or scheduled-job caller found importing `finance_hub`'s
  service module outside its own router.

## Distinguishing user-triggered vs. system calls
All 37 combined mutations across both modules require `get_current_user`
(an authenticated human principal) — no route in either module is a
`BACKGROUND_WORKER` or `CALLBACK_OR_WEBHOOK` persona; none are
internal-only trusted calls without a user context.

## Not claimed
This is not a repository-wide service-layer audit — scoped to the two
modules named in this slice's mission.
