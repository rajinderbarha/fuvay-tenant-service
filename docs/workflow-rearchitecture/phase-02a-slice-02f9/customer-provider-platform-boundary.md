# Customer, Provider, and Platform Boundary — Workstream 5

## Verified separation

| Capability | Owner | Verified in this router |
|---|---|---|
| Create complaint | Customer (a different, `complaints.customer_router` — not audited this slice) | Not present in `provider_router.py` — confirmed |
| Submit customer evidence | Customer | Not present here |
| Reply as customer | Customer (`sender_type=ACTOR_CUSTOMER`, a distinct code path in `complaint_service.py` not called from this router) | `respond_to_complaint` always writes `sender_type=ACTOR_PROVIDER` — confirmed no impersonation path exists |
| Accept/reject resolution as customer | Customer (`customer_respond_to_settlement`, a distinct method not called from `provider_router.py`) | Confirmed — `respond_to_settlement` calls `tenant_respond_to_settlement`, a **separate** method; the provider cannot call the customer's acceptance method through this router |
| Provider acknowledge/reply/evidence/notes | Provider | `respond_to_complaint`, `offer_resolution` — confirmed provider-scoped |
| Provider propose resolution/settlement | Provider | `offer_resolution`, `create_settlement_proposal` — confirmed |
| Provider request rework | Provider | `schedule_rework`/`start_rework`/`complete_rework` operate on an **already-existing** `ServiceReworkRequest` (created via `create_rework_request_from_complaint`, not reachable from this router — see `rework-boundary.md`) |
| Platform adjudicate/force-resolve/close severe cases | Platform (`admin_finalize_settlement`, `admin_start_ai_settlement`, `admin_approve_refund`, `approve_rework`/`reject_rework`/`cancel_rework` — all in the service layer, none reachable from `provider_router.py`) | Confirmed absent from this router |
| Issue platform service credit | Platform/dual-acceptance mechanism (`_execute_settlement_payout`, internal credit only, blocks monetary remedies) | Reachable via `respond_to_settlement`, but **not** a direct, unilateral provider action — requires the customer to have already accepted too (`_check_dual_acceptance`) |
| Deduct tenant credit | Same dual-acceptance mechanism, funded from "the provider's own credit wallet" per the code's own comment — a tenant deducting **its own** credit, not another tenant's | Confirmed — no cross-tenant credit deduction path exists |

## Requirements verification

| Requirement | Status |
|---|---|
| Provider routes must not impersonate customer actions | Confirmed — `sender_type`/`proposed_by`/`ACTOR_PROVIDER` are hardcoded server-side in every provider-facing method, never client-suppliable |
| Provider roles must not perform platform adjudication unless explicitly authorized | Confirmed — no admin/platform method is reachable from this router |
| Customer routes must not mutate provider internal notes | N/A — no internal-note capability exists at all through any route audited (see `note-evidence-privacy.md`) |
| Tenant users must not issue platform-controlled service credits | Confirmed — the only credit mechanism requires **dual acceptance**, is capped to the provider's own wallet/deposit, and explicitly blocks monetary remedies |
| Tenant users must not deduct another tenant's credit | Confirmed — `tenant_id`/`complaint.tenant_id` scoping (now fully closed this slice) ensures the payout only ever touches the complaint's own tenant |
| Platform routes must remain separately permission-gated | Confirmed — platform methods live in the service layer with no corresponding router endpoint in `provider_router.py` (their own router, if any, was not audited — out of scope) |
| Frontend controls must respect the boundary | Verified for the one page with active controls (`complaints/[complaint_id]/page.tsx`) — see `frontend-exposure-audit.md` |

## Conclusion
The customer/provider/platform boundary is correctly maintained by
construction (hardcoded actor types, separate service methods, no
platform method reachable from this router). No boundary violation was
found requiring a fix; the security work this slice needed was
authorization (who can call these provider methods at all) and
tenant/complaint ownership (which record they operate on), not
persona-impersonation.
