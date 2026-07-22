# Backend Blockers Before Phase 2 (and Phase 3)

Blockers requiring backend engineering, not frontend/nav work. Ranked by what they block.

## Blocks Phase 3 (Booking Exception Resolution) — not Phase 2
1. **Booking/Job/ServiceJob relationship investigation.** A live route dump found a real `POST /v1/bookings/{booking_id}/convert-to-job` endpoint — proving `Booking` and field_ops `Job` are explicitly linked for at least some flow, while `ServiceBooking`/`ServiceJob` (home_services vertical) is created independently via `/v1/customer/home-services/booking-drafts/*` with no `Booking`/`Job` row involved. The open question is now specific: **does `Booking → convert-to-job → Job` handle the same real-world bookings as `ServiceJob`, or a genuinely separate scope (e.g. non-home-services verticals)?** Determine this by checking which vertical/tenant configuration routes through which pipeline at creation time. This is the single highest-priority backend investigation in this document set — it blocks the entire Booking Exception Resolution workflow and materially affects how "Jobs" navigation is scoped long-term. See `booking-job-canonical-decision.md`.
2. **Read-aggregation BFF for unified Jobs list**, contingent on #1's answer.

## Should ship alongside Phase 2, does not block it
3. **Block `POST /v1/reviews`** (legacy review create) at the API layer — confirmed zero frontend callers, zero risk, straightforward backend change. See `review-canonical-decision.md`.
4. **Confirm ownership of `/v1/admin/chat/threads`** (core `chat` admin routes vs `platform_notifications` admin_chat_router) — low effort, resolves Domain 4 of `chat-domain-ownership.md`, non-blocking since admin chat isn't part of the 3 reference workflows.
5. **Reconcile duplicate setup-template/bulk-wizard systems** (`admin_catalog` vs `service_setup` engines) — needed for the Provider Setup wizard's templating feature; wizard can ship without templating if this isn't done in time.
6. **Reconcile duplicate customer-flow engines** (`admin_catalog/customer_flow_router.py` vs standalone `customer_flow` engine) — confirm which one the current booking flow's category routing actually calls before the Setup Wizard's step 1 is finalized.
7. **`require_super_admin` gating gap** — the 4 newer least-privilege admin roles (admin_operations/finance/security/readonly) are locked out of most admin surfaces because most `admin_router.py` files gate on the strict `require_super_admin` check rather than `require_permission`. Not blocking Phase 2 (frontend nav degrades gracefully per risk register), but should be scheduled as its own backend workstream.
8. **`StaffPermission` override hydration.** `get_current_user` never populates `UserContext.permission_overrides` in the code path found in Phase 1 — per-user permission overrides may be silently inert. Needs a focused investigation; affects the Governance workspace's accuracy but not its navigation structure.

## Reversed finding — no longer a blocker
11. **Parts Request/Approval — RESOLVED, reversing both Phase 1 and the initial Phase 1A draft.** A live route dump plus source read confirmed a full `PartsRequest` model (`service_job_parts_requests` table) with create/list/approve/reject/install endpoints, linked to `ServiceJob.job_id` via `/v1/staff/service-jobs/{id}/parts-requests` and `/v1/provider/service-jobs/{id}/parts-requests/*`. See `quote-parts-scope-decision.md`. One small follow-up remains: confirm the customer-facing approval path for requests with `customer_approval_required=true` (non-blocking).

## Explicit product decision needed (not purely technical)
9. **AI chat vs AI conversation** — both `ai_chat` (`/v1/ai/chat`) and `ai_conversation` (`/v1/customer/ai-chat/sessions`) are simultaneously called by the mobile customer app. Is this one feature or two intentionally distinct AI experiences? See `chat-domain-ownership.md` Domain 5. Non-blocking for Phase 2.
10. **Security deposit canonical replacement — RESOLVED.** Verification confirmed `finance_hub`'s `/v1/admin/finance/deposits*` is the live, already-used replacement for the 410'd `package_commerce` admin endpoints; `package_commerce/tenant_router.py`'s tenant-side view remains live and unblocked. No further backend blocker here — update `finance-capability-ownership.csv` and remove the "BLOCKED" marker from the Deposits tab in Phase 2 scope.

## Downgrade notice
Item 10 above was listed as a Phase 1 blocker and is now resolved by verification evidence — `phase-02-scope.md`, `phase-02-risk-register.md`, and `finance-capability-ownership.csv` should treat the Deposits tab as shippable in Phase 2, not blocked.
