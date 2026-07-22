# Workflow Gaps and Blockers

Ranked by what would break the reference workflows if we proceeded to Phase 2 implementation without resolving them first.

## Critical (block reference-workflow implementation)

1. **Three parallel booking/job models still live** (Booking legacy / field_ops Job / ServiceJob canonical). The Booking Exception Resolution workspace must be built against ServiceJob only. Before Phase 2, confirm zero live frontend callers of `/v1/bookings` and `/v1/jobs` (field_ops); if any exist, they must be migrated first. SOURCE_VERIFIED (duplication), UNVERIFIED (caller count).
2. **Two live review stacks** (`/v1/reviews` legacy vs `/v1/customer/reviews`+ canonical). `/admin/reviews` super-admin page's actual backing API is unconfirmed — must verify before deciding its disposition, since building "Reviews" into the Customers workspace on the wrong stack would perpetuate the split.
3. **No structured Parts Request/Approval entity.** The spec calls for a Parts step in both the Guided Setup and Exception workspace patterns; today "parts required" only flips a status flag. Recommend explicitly descoping Parts from Phase 2 workspace UI until backend work delivers it, rather than faking a UI for a non-existent flow.
4. **Chat has 4 competing engines** with no documented canonical choice. Both "Contact customer" (Exception workspace) and "Customers > Chat" (nav) need one messaging backend. Frontend evidence (staff-app + tenant-portal calling `/v1/staff/chat/threads`) suggests `platform_notifications` is the de facto winner, but this needs an explicit product decision, not an inference.

## High (should resolve before broad rollout, not blocking a first pilot)

5. Two competing "setup templates/bulk wizard" systems (`admin_catalog` vs `service_setup` engines) — affects the Provider Service & Pricing Setup wizard's template/duplicate feature.
6. Two competing "customer flow" engines (`admin_catalog/customer_flow_router.py` vs standalone `customer_flow` engine) — affects booking-flow category routing.
9. Three finance surfaces sharing `/v1/admin/finance` (field_ops, invoice_payment, finance_hub) — main.py resolves the immediate route collision by mount order, but the Finance workspace consolidation (page-disposition-matrix.csv) needs one canonical source per data type before building tabs.
10. Security deposit: legacy endpoints are `[DEPRECATED_410]` and no confirmed canonical replacement was found in this pass — the onboarding wizard's step 10 and the tenant Credits workspace both depend on this being resolved.
11. Super-admin nav/route drift (~10 orphaned pages: real-estate, coaching, bookability, reports, ai, ai-chat, service-invoices, provider-wallets, commission-records, payments, financial-events) — low-risk fix, no backend dependency, but currently makes ~10 working features invisible to admins who don't know the direct URL.

## Medium (data-quality follow-ups, not blocking any reference workflow)

12. `require_super_admin` strict-role gate locks the 4 newer least-privilege admin roles (`admin_operations/finance/security/readonly`) out of most admin surfaces — affects how much of the simplified admin nav those roles can actually see; recommend widening `require_super_admin`-gated routers to also accept matching `require_permission` calls as those roles come into real use.
13. `StaffPermission` per-user override table may never be hydrated into `UserContext.permission_overrides` at request time (found no code path doing so in this pass) — if true, per-user permission overrides are silently inert. Needs a focused backend investigation, unrelated to navigation/workflow design but relevant to the Governance workspace's promise that permission overrides work.
14. Mobile staff app is missing skills/service-areas/availability/documents/session-management screens that the web staff portal has — real feature-parity gap for the Technician role's Profile workspace.
15. Customer app has two full parallel screen sets (current `MainNavigator` + nested legacy `AppNavigator`/`TabNavigator`, 19 screens) — intentional per code comments, not accidental, but should be consolidated eventually; does not block Phase 2 nav work since the legacy stack isn't in primary nav today either.
16. Duplicate nav entries in tenant-portal today (`/reviews` + `/provider/reviews`, `/marketing` + `/provider/marketing`, `/chat` + `/provider/chat`) — cosmetic, easy MERGE-disposition fix once approved.

## Explicitly out of scope for this pass (flagged UNVERIFIED, recommend follow-up research before relying on them)
- Exact Tenant onboarding status-transition gating rules (which fields block which transitions) — not traced to `tenant_engine/service.py` in this pass.
- Media/profile-photo-upload canonical-vs-legacy check (item 9 of Phase 3 spec) — not investigated.
- Whether `/v1/bookings` and `/v1/jobs` (field_ops) truly have zero live frontend callers, across all 5 apps — the frontend audit found none in the pages it sampled, but did not exhaustively grep every file.
