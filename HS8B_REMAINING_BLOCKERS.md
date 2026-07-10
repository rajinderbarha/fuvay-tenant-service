# HS8B — Remaining Blockers

## Closed this pass (both were hard-gated HS8 blockers with their own NOT_READY codes)
1. ~~Parts-request approval workflow does not exist~~ — **FIXED.** Real
   model, real create/approve/reject/install endpoints, all live-verified
   in both the pass and reject direction.
2. ~~Completion is not a single validated action~~ — **FIXED.** Real
   `/complete` endpoint, work summary and collected amount both
   hard-required (live-verified 422s with the ticket's exact codes),
   payment mode locked to `customer_pays_provider_directly`, unresolved
   parts requests block completion.

## Still open
3. **Customer approval for parts requests** — schema exists
   (`customer_approval_required` flag + statuses) but no endpoint or UI
   calls it. Documented as future scope per the ticket's own escape hatch.
4. **"Request More Info" (tenant) and "Cancel own pending request"
   (technician)** parts actions not implemented — only Approve/Reject/Install.
5. **No customer-facing tracking UI** — same established gap from HS7,
   not attempted this pass (time budget went to the two hard-gated
   blockers plus tenant/technician UI).
6. **Permission-aware UI/RBAC not investigated** — same as HS8, unchanged.
7. **Collected-amount-vs-selected-price difference policy not
   implemented** — the ticket's `amount_difference_reason`/
   `approved_extra_charges`/`discount_reason` fields don't exist; only
   the baseline "collected amount ≥ 0" check is enforced, per the
   ticket's own fallback instruction ("If this policy is not implemented
   yet, at minimum validate collected_amount exists and is >= 0... and
   document exact gap").
8. **No live browser/UI click-through verification** — TypeScript
   compile + source inspection only, not a driven browser session.
9. **Completion photo requirement is opt-in and currently disabled by
   default** — no policy-configuration surface exists to enable it per
   tenant/service.
10. **Tenant job-queue list page** (`service-jobs/page.tsx`) wasn't
    updated with Parts Status / Collected Amount columns — only the
    per-job execution page was extended.

## What is solid and fixed this pass
- Real parts-request model + full create → approve/reject → install
  lifecycle, live-verified in both directions (including the specific
  "rejected cannot be installed" gate the ticket calls out).
- Real single validated completion action — cannot happen without work
  summary or collected amount (live-verified 422s), payment mode locked,
  unresolved parts requests block completion.
- New, real, TypeScript-clean technician job UI at
  `/staff/home-services/jobs` with a status-driven action flow that
  mirrors the backend's transition graph exactly.
- Real bug fixed in the pre-existing tenant execution page: `job` data
  was never actually fetched, so the status action bar could never
  render for any job — fixed, plus new Parts Requests and Completion
  Proof sections added.
- Zero backend regressions (288/288 passing after updating 1 test for a
  correct, intentional behavior change); 0 TypeScript errors.
